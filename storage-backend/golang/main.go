package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v4"
	"github.com/jackc/pgx/v4/pgxpool"
	"golang.org/x/crypto/bcrypt"
)

// --- JWT Secret ---
var jwtKey = []byte(os.Getenv("JWT_SECRET_KEY"))

// --- Structs for Data Models ---

type User struct {
	ID           int       `json:"id"`
	Username     string    `json:"username"`
	PasswordHash string    `json:"-"` // Do not expose password hash
	CreatedAt    time.Time `json:"created_at"`
}

type Container struct {
	Length    float64 `json:"length"`
	Width     float64 `json:"width"`
	Height    float64 `json:"height"`
	MaxWeight float64 `json:"maxWeight"`
}

type Item struct {
	ID       string  `json:"id"`
	Quantity int     `json:"quantity"`
	Length   float64 `json:"length"`
	Width    float64 `json:"width"`
	Height   float64 `json:"height"`
	Weight   float64 `json:"weight"`
	Group    string  `json:"group"`
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

// --- Structs for Auth ---

type LoginRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type Claims struct {
	UserID int `json:"user_id"`
	jwt.RegisteredClaims
}

// --- Database Connection ---

func connectDB() *pgxpool.Pool {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgres://user:password@db:5432/packaging_db" // Use service name 'db' for docker-compose
	}

	pool, err := pgxpool.Connect(context.Background(), dbURL)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}

	log.Println("Successfully connected to PostgreSQL database!")
	return pool
}

// --- Database Setup ---

func setupDatabase(pool *pgxpool.Pool) {
	// Drop existing table to start fresh (optional, for development)
	// _, err := pool.Exec(context.Background(), "DROP TABLE IF EXISTS calculation_history, items, groups, calculations, constraints, containers, users;")
	// if err != nil {
	// 	log.Fatalf("Failed to drop tables: %v\n", err)
	// }

	// Create Users Table
	createUsersTable := `
	CREATE TABLE IF NOT EXISTS users (
		id SERIAL PRIMARY KEY,
		username VARCHAR(255) UNIQUE NOT NULL,
		password_hash VARCHAR(255) NOT NULL, 
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err := pool.Exec(context.Background(), createUsersTable)
	if err != nil {
		log.Fatalf("Failed to create users table: %v\n", err)
	}
	log.Println("'users' table is ready.")

	// Create Containers Table
	createContainersTable := `
	CREATE TABLE IF NOT EXISTS containers (
		id SERIAL PRIMARY KEY,
		width DECIMAL,
		height DECIMAL,
		length DECIMAL,
		max_weight DECIMAL
	);`
	_, err = pool.Exec(context.Background(), createContainersTable)
	if err != nil {
		log.Fatalf("Failed to create containers table: %v\n", err)
	}
	log.Println("'containers' table is ready.")

	// Create Constraints Table
	createConstraintsTable := `
	CREATE TABLE IF NOT EXISTS constraints (
		id SERIAL PRIMARY KEY,
		enforce_lifo BOOLEAN,
		enforce_priority BOOLEAN,
		enforce_stacking BOOLEAN,
		enforce_load_capacity BOOLEAN
	);`
	_, err = pool.Exec(context.Background(), createConstraintsTable)
	if err != nil {
		log.Fatalf("Failed to create constraints table: %v\n", err)
	}
	log.Println("'constraints' table is ready.")

	// Create Calculations Table
	createCalculationsTable := `
	CREATE TABLE IF NOT EXISTS calculations (
		id SERIAL PRIMARY KEY,
		user_id INTEGER REFERENCES users(id),
		container_id INTEGER REFERENCES containers(id),
		constraints_id INTEGER REFERENCES constraints(id),
		algorithm VARCHAR(50),
		response_body JSONB,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createCalculationsTable)
	if err != nil {
		log.Fatalf("Failed to create calculations table: %v\n", err)
	}
	log.Println("'calculations' table is ready.")

	// Create Items Table
	createItemsTable := `
	CREATE TABLE IF NOT EXISTS items (
		id SERIAL PRIMARY KEY,
		calculation_id INTEGER REFERENCES calculations(id),
		item_id_string VARCHAR(255),
		group_name VARCHAR(255),
		width DECIMAL,
		height DECIMAL,
		length DECIMAL,
		weight DECIMAL,
		quantity INTEGER
	);`
	_, err = pool.Exec(context.Background(), createItemsTable)
	if err != nil {
		log.Fatalf("Failed to create items table: %v\n", err)
	}
	log.Println("'items' table is ready.")

	// Create Groups Table
	createGroupsTable := `
	CREATE TABLE IF NOT EXISTS groups (
		id SERIAL PRIMARY KEY,
		calculation_id INTEGER REFERENCES calculations(id),
		group_id_string VARCHAR(255),
		name VARCHAR(255),
		color VARCHAR(50)
	);`
	_, err = pool.Exec(context.Background(), createGroupsTable)
	if err != nil {
		log.Fatalf("Failed to create groups table: %v\n", err)
	}
	log.Println("'groups' table is ready.")
}

// --- Password & JWT Helpers ---

func HashPassword(password string) (string, error) {
	bytes, err := bcrypt.GenerateFromPassword([]byte(password), 14)
	return string(bytes), err
}

func CheckPasswordHash(password, hash string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
	return err == nil
}

func generateJWT(userID int) (string, error) {
	expirationTime := time.Now().Add(24 * time.Hour)
	claims := &Claims{
		UserID: userID,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expirationTime),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(jwtKey)
}

// --- Gin Handlers ---

func handleRegister(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req LoginRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
			return
		}

		hashedPassword, err := HashPassword(req.Password)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to hash password"})
			return
		}

		insertSQL := `INSERT INTO users (username, password_hash) VALUES ($1, $2) RETURNING id;`
		var userID int
		err = db.QueryRow(context.Background(), insertSQL, req.Username, hashedPassword).Scan(&userID)
		if err != nil {
			log.Printf("Failed to register user: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Username may already be taken."})
			return
		}

		c.JSON(http.StatusCreated, gin.H{"message": "User registered successfully", "user_id": userID})
	}
}

func handleLogin(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req LoginRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
			return
		}

		var user User
		var passwordHash string
		querySQL := `SELECT id, username, password_hash FROM users WHERE username=$1;`
		err := db.QueryRow(context.Background(), querySQL, req.Username).Scan(&user.ID, &user.Username, &passwordHash)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
			return
		}

		if !CheckPasswordHash(req.Password, passwordHash) {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
			return
		}

		token, err := generateJWT(user.ID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to generate token"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"token": token})
	}
}

func handleGoCalculation(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		var requestData CalculationRequest

		if err := c.ShouldBindJSON(&requestData); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body: " + err.Error()})
			return
		}

		// Get user ID from context (set by authMiddleware)
		userID, exists := c.Get("user_id")
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
			return
		}

		// Use a transaction to ensure all inserts succeed or none do
		tx, err := db.Begin(context.Background())
		if err != nil {
			log.Printf("Failed to begin transaction: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to start database transaction."})
			return
		}
		defer tx.Rollback(context.Background()) // Rollback on error

		// 1. Insert Container
		var containerID int
		containerSQL := `INSERT INTO containers (width, height, length, max_weight) VALUES ($1, $2, $3, $4) RETURNING id;`
		err = tx.QueryRow(context.Background(), containerSQL, requestData.Container.Width, requestData.Container.Height, requestData.Container.Length, requestData.Container.MaxWeight).Scan(&containerID)
		if err != nil {
			log.Printf("Failed to insert container: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save container data."})
			return
		}

		// 2. Insert Constraints
		var constraintsID int
		constraintsSQL := `INSERT INTO constraints (enforce_lifo, enforce_priority, enforce_stacking, enforce_load_capacity) VALUES ($1, $2, $3, $4) RETURNING id;`
		err = tx.QueryRow(context.Background(), constraintsSQL, requestData.Constraints.EnforceLIFO, requestData.Constraints.EnforcePriority, requestData.Constraints.EnforceStacking, requestData.Constraints.EnforceLoadCapacity).Scan(&constraintsID)
		if err != nil {
			log.Printf("Failed to insert constraints: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save constraints data."})
			return
		}

		// 3. Insert Calculation
		var calculationID int
		calculationSQL := `INSERT INTO calculations (user_id, container_id, constraints_id, algorithm) VALUES ($1, $2, $3, $4) RETURNING id;`
		err = tx.QueryRow(context.Background(), calculationSQL, userID, containerID, constraintsID, requestData.Algorithm).Scan(&calculationID)
		if err != nil {
			log.Printf("Failed to insert calculation: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save calculation data."})
			return
		}

		// 4. Insert Items
		for _, item := range requestData.Items {
			itemSQL := `INSERT INTO items (calculation_id, item_id_string, group_name, width, height, length, weight, quantity) VALUES ($1, $2, $3, $4, $5, $6, $7, $8);`
			_, err = tx.Exec(context.Background(), itemSQL, calculationID, item.ID, item.Group, item.Width, item.Height, item.Length, item.Weight, item.Quantity)
			if err != nil {
				log.Printf("Failed to insert item: %v", err)
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save item data."})
				return
			}
		}

		// 5. Insert Groups
		for _, group := range requestData.Groups {
			groupSQL := `INSERT INTO groups (calculation_id, group_id_string, name, color) VALUES ($1, $2, $3, $4);`
			_, err = tx.Exec(context.Background(), groupSQL, calculationID, group.ID, group.Name, group.Color)
			if err != nil {
				log.Printf("Failed to insert group: %v", err)
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save group data."})
				return
			}
		}

		// All inserts successful, commit the transaction
		err = tx.Commit(context.Background())
		if err != nil {
			log.Printf("Failed to commit transaction: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to finalize database transaction."})
			return
		}

		log.Printf("Saved new calculation with ID: %d for user ID: %d", calculationID, userID)

		// --- Call Python Backend (same as before) ---
		pythonURL := os.Getenv("PYTHON_BACKEND_URL")
		if pythonURL == "" {
			pythonURL = "http://localhost:8000/calculate/python"
		}
		jsonReq, _ := json.Marshal(requestData)

		resp, err := http.Post(pythonURL, "application/json", bytes.NewBuffer(jsonReq))
		if err != nil {
			log.Printf("Failed to call Python backend: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to communicate with the calculation service."})
			return
		}
		defer resp.Body.Close()

		pythonResponseBody, err := io.ReadAll(resp.Body)
		if err != nil {
			log.Printf("Failed to read Python response: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read calculation result."})
			return
		}

		// Update the calculation with the response from Python
		updateSQL := `UPDATE calculations SET response_body = $1 WHERE id = $2;`
		_, err = db.Exec(context.Background(), updateSQL, pythonResponseBody, calculationID)
		if err != nil {
			log.Printf("Failed to update response in DB: %v", err)
			// Don't block, just log
		}
		log.Printf("Updated DB record for calculation ID: %d", calculationID)

		c.Data(resp.StatusCode, "application/json", pythonResponseBody)
	}
}

// --- Gin Middleware ---

func authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authorization header is missing"})
			return
		}

		tokenString := strings.TrimPrefix(authHeader, "Bearer ")
		if tokenString == authHeader {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Bearer token not found"})
			return
		}

		claims := &Claims{}
		token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return jwtKey, nil
		})

		if err != nil || !token.Valid {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Invalid token"})
			return
		}

		// Pass user ID to the next handler
		c.Set("user_id", claims.UserID)
		c.Next()
	}
}

func main() {
	if os.Getenv("JWT_SECRET_KEY") == "" {
		log.Println("Warning: JWT_SECRET_KEY is not set. Using a default value. Please set this in your environment.")
		jwtKey = []byte("default-secret-key-for-dev")
	}

	dbPool := connectDB()
	defer dbPool.Close()

	setupDatabase(dbPool)

	router := gin.Default()

	router.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "http://localhost:3000")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	// Public routes
	authRoutes := router.Group("/auth")
	{
		authRoutes.POST("/register", handleRegister(dbPool))
		authRoutes.POST("/login", handleLogin(dbPool))
	}

	// Protected routes
	apiRoutes := router.Group("/api")
	apiRoutes.Use(authMiddleware())
	{
		apiRoutes.POST("/calculate/golang", handleGoCalculation(dbPool))
	}

	// Legacy route for now, should be deprecated
	// router.POST("/calculate/golang", handleGoCalculation(dbPool))

	log.Println("Go server starting on port 8080...")
	router.Run(":8080")
}
