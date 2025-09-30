package main

import (
	"bytes"
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"io"


	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v4/pgxpool"
)

// --- Structs to match the JSON structure ---

type Container struct {
	Length    float64 `json:"length"`
	Width     float64 `json:"width"`
	Height    float64 `json:"height"`
	MaxWeight float64 `json:"maxWeight"`
}

type Item struct {
	ID               string  `json:"id"`
	Quantity         int     `json:"quantity"`
	Length           float64 `json:"length"`
	Width            float64 `json:"width"`
	Height           float64 `json:"height"`
	Weight           float64 `json:"weight"`
	Group            string  `json:"group"`
	AllowedRotations []int   `json:"allowed_rotations,omitempty"`
	MaxStackWeight   float64 `json:"max_stack_weight,omitempty"`
	Priority         int     `json:"priority,omitempty"`
	DestinationGroup int     `json:"destination_group,omitempty"`
}

type Group struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Color string `json:"color"`
}

type Constraints struct {
	EnforceLoadCapacity bool `json:"enforceLoadCapacity"`
	EnforceStacking     bool `json:"enforceStacking"`
	EnforcePriority     bool `json:"enforcePriority"`
	EnforceLIFO         bool `json:"enforceLIFO"`
}

type CalculationRequest struct {
	Container   Container   `json:"container"`
	Items       []Item      `json:"items"`
	Groups      []Group     `json:"groups"`
	Algorithm   string      `json:"algorithm"`
	Constraints Constraints `json:"constraints"`
}

// --- Database Connection ---

func connectDB() *pgxpool.Pool {
	// DATABASE_URL example: "postgres://user:password@localhost:5432/packaging_db"
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgres://user:password@localhost:5432/packaging_db"
	}

	pool, err := pgxpool.Connect(context.Background(), dbURL)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v\n", err)
	}

	log.Println("Successfully connected to PostgreSQL database!")
	return pool
}

func setupDatabase(pool *pgxpool.Pool) {
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS calculation_history (
		id SERIAL PRIMARY KEY,
		request_body JSONB NOT NULL,
		response_body JSONB,
		algorithm VARCHAR(50),
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);
	`

	_, err := pool.Exec(context.Background(), createTableSQL)
	if err != nil {
		log.Fatalf("Failed to create table: %v\n", err)
	}
	log.Println("'calculation_history' table is ready.")
}


func main() {
	// Connect to the database
	dbPool := connectDB()
	defer dbPool.Close()

	// Set up the database table
	setupDatabase(dbPool)

	// Initialize Gin router
outer := gin.Default()

	// Add CORS middleware
outer.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	// Define the endpoint
outer.POST("/calculate/golang", handleGoCalculation(dbPool))

	// Start the server
	log.Println("Go server starting on port 8080...")
outer.Run(":8080")
}

func handleGoCalculation(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		var requestData CalculationRequest

		// 1. Bind the incoming JSON to the struct
		if err := c.ShouldBindJSON(&requestData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body: " + err.Error()})
			return
		}

		// 2. Save the initial request to the database
		requestBodyBytes, _ := json.Marshal(requestData)
		
		insertSQL := `INSERT INTO calculation_history (request_body, algorithm) VALUES ($1, $2) RETURNING id;`
		var calculationID int
		err := db.QueryRow(context.Background(), insertSQL, requestBodyBytes, requestData.Algorithm).Scan(&calculationID)
		if err != nil {
			log.Printf("Failed to insert request into DB: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save request."})
			return
		}
		log.Printf("Saved request to DB with ID: %d", calculationID)


		// 3. Forward the request to the Python backend
		pythonURL := "http://host.docker.internal:8000/calculate/python"
		jsonReq, _ := json.Marshal(requestData)

		resp, err := http.Post(pythonURL, "application/json", bytes.NewBuffer(jsonReq))
		if err != nil {
			log.Printf("Failed to call Python backend: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to communicate with the calculation service."})
			return
		}
		defer resp.Body.Close()

		// 4. Read the response from the Python backend
		pythonResponseBody, err := io.ReadAll(resp.Body)
		if err != nil {
			log.Printf("Failed to read Python response: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read calculation result."})
			return
		}

		// 5. Update the database record with the Python response
		updateSQL := `UPDATE calculation_history SET response_body = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2;`
		_, err = db.Exec(context.Background(), updateSQL, pythonResponseBody, calculationID)
		if err != nil {
			// Log the error, but don't block the user. The main flow is complete.
			log.Printf("Failed to update response in DB: %v", err)
		}
		log.Printf("Updated DB record for ID: %d", calculationID)


		// 6. Return the Python response to the frontend
		// We send back the raw JSON response from Python
		c.Data(resp.StatusCode, "application/json", pythonResponseBody)
	}
}