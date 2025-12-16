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
		log.Fatal("DATABASE_URL environment variable is required. Please set it in your .env file or environment.")
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
		user_id INTEGER REFERENCES users(id),
		width DECIMAL NOT NULL,
		height DECIMAL NOT NULL,
		length DECIMAL NOT NULL,
		max_weight DECIMAL NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createContainersTable)
	if err != nil {
		log.Fatalf("Failed to create containers table: %v\n", err)
	}
	log.Println("'containers' table is ready.")

	// Create Item Groups Table (MUST be created before items table)
	createItemGroupsTable := `
	CREATE TABLE IF NOT EXISTS item_groups (
		id SERIAL PRIMARY KEY,
		name VARCHAR(255) UNIQUE NOT NULL,
		color VARCHAR(50) NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createItemGroupsTable)
	if err != nil {
		log.Fatalf("Failed to create item_groups table: %v\n", err)
	}

	// Insert default item group (check if exists first)
	var defaultExists int
	err = pool.QueryRow(context.Background(), "SELECT COUNT(*) FROM item_groups WHERE name = 'default';").Scan(&defaultExists)
	if err == nil && defaultExists == 0 {
		defaultGroupSQL := `INSERT INTO item_groups (name, color) VALUES ('default', '#808080');`
		_, err = pool.Exec(context.Background(), defaultGroupSQL)
		if err != nil {
			log.Printf("Failed to insert default item group: %v", err)
		}
	}

	log.Println("'item_groups' table is ready.")

	// Create Items Table (MUST be created after item_groups table)
	createItemsTable := `
	CREATE TABLE IF NOT EXISTS items (
		id SERIAL PRIMARY KEY,
		container_id INTEGER REFERENCES containers(id),
		name VARCHAR(255) NOT NULL,
		width DECIMAL NOT NULL,
		height DECIMAL NOT NULL,
		length DECIMAL NOT NULL,
		weight DECIMAL NOT NULL,
		quantity INTEGER NOT NULL,
		group_id INTEGER REFERENCES item_groups(id),
		max_stack_weight DECIMAL,
		priority INTEGER,
		allowed_rotations INTEGER[],
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createItemsTable)
	if err != nil {
		log.Fatalf("Failed to create items table: %v\n", err)
	}

	// Check and add missing columns if needed
	alterItemsTable := `
	DO $$ 
	BEGIN 
		-- Add missing columns if they don't exist
		IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'items' AND column_name = 'container_id') THEN
			ALTER TABLE items ADD COLUMN container_id INTEGER REFERENCES containers(id);
		END IF;
		IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'items' AND column_name = 'name') THEN
			ALTER TABLE items ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT '';
		END IF;
		IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'items' AND column_name = 'group_id') THEN
			ALTER TABLE items ADD COLUMN group_id INTEGER REFERENCES item_groups(id);
		END IF;
		
		-- Remove old columns if they exist
		IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'items' AND column_name = 'calculation_id') THEN
			ALTER TABLE items DROP COLUMN IF EXISTS calculation_id;
		END IF;
		IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'items' AND column_name = 'item_id_string') THEN
			ALTER TABLE items DROP COLUMN IF EXISTS item_id_string;
		END IF;
		IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'items' AND column_name = 'group_name') THEN
			ALTER TABLE items DROP COLUMN IF EXISTS group_name;
		END IF;
	END $$;`
	_, err = pool.Exec(context.Background(), alterItemsTable)
	if err != nil {
		log.Printf("Failed to alter items table: %v", err)
	}

	log.Println("'items' table is ready.")

	// Create Calculation Requests Table
	createCalculationRequestsTable := `
	CREATE TABLE IF NOT EXISTS calculation_requests (
		id SERIAL PRIMARY KEY,
		user_id INTEGER REFERENCES users(id),
		container_id INTEGER REFERENCES containers(id),
		algorithm VARCHAR(50) NOT NULL,
		enforce_load_capacity BOOLEAN NOT NULL,
		enforce_stacking BOOLEAN NOT NULL,
		enforce_priority BOOLEAN NOT NULL,
		enforce_lifo BOOLEAN NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createCalculationRequestsTable)
	if err != nil {
		log.Fatalf("Failed to create calculation_requests table: %v\n", err)
	}
	log.Println("'calculation_requests' table is ready.")

	// Create Calculation Results Table
	createCalculationResultsTable := `
	CREATE TABLE IF NOT EXISTS calculation_results (
		id SERIAL PRIMARY KEY,
		request_id INTEGER REFERENCES calculation_requests(id),
		fill_rate DECIMAL NOT NULL,
		total_weight DECIMAL NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createCalculationResultsTable)
	if err != nil {
		log.Fatalf("Failed to create calculation_results table: %v\n", err)
	}
	log.Println("'calculation_results' table is ready.")

	// Create Placed Items Table
	createPlacedItemsTable := `
	CREATE TABLE IF NOT EXISTS placed_items (
		id SERIAL PRIMARY KEY,
		result_id INTEGER REFERENCES calculation_results(id),
		item_id INTEGER REFERENCES items(id),
		position_x DECIMAL NOT NULL,
		position_y DECIMAL NOT NULL,
		position_z DECIMAL NOT NULL,
		rotation_type INTEGER NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createPlacedItemsTable)
	if err != nil {
		log.Fatalf("Failed to create placed_items table: %v\n", err)
	}
	log.Println("'placed_items' table is ready.")

	// Create Constraints Table (MUST be created before calculations)
	createConstraintsTable := `
	CREATE TABLE IF NOT EXISTS constraints (
		id SERIAL PRIMARY KEY,
		enforce_lifo BOOLEAN NOT NULL,
		enforce_priority BOOLEAN NOT NULL,
		enforce_stacking BOOLEAN NOT NULL,
		enforce_load_capacity BOOLEAN NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createConstraintsTable)
	if err != nil {
		log.Fatalf("Failed to create constraints table: %v\n", err)
	}
	log.Println("'constraints' table is ready.")

	// Create Calculations Table (MUST be created before groups)
	createCalculationsTable := `
	CREATE TABLE IF NOT EXISTS calculations (
		id SERIAL PRIMARY KEY,
		user_id INTEGER REFERENCES users(id),
		container_id INTEGER REFERENCES containers(id),
		constraints_id INTEGER REFERENCES constraints(id),
		algorithm VARCHAR(50) NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createCalculationsTable)
	if err != nil {
		log.Fatalf("Failed to create calculations table: %v\n", err)
	}
	log.Println("'calculations' table is ready.")

	// Create Groups Table (references calculations table)
	createGroupsTable := `
	CREATE TABLE IF NOT EXISTS groups (
		id SERIAL PRIMARY KEY,
		calculation_id INTEGER REFERENCES calculations(id),
		group_id_string VARCHAR(255) NOT NULL,
		name VARCHAR(255) NOT NULL,
		color VARCHAR(50) NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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

// --- Database Helper Functions ---

func saveCalculationResults(db *pgxpool.Pool, calculationID int, pythonResponse map[string]interface{}) error {
	tx, err := db.Begin(context.Background())
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %v", err)
	}
	defer tx.Rollback(context.Background())

	// Insert to calculation_requests first (log the request)
	requestSQL := `INSERT INTO calculation_requests (user_id, container_id, algorithm, enforce_load_capacity, enforce_stacking, enforce_priority, enforce_lifo) 
				   SELECT user_id, container_id, algorithm, c.enforce_load_capacity, c.enforce_stacking, c.enforce_priority, c.enforce_lifo 
				   FROM calculations calc 
				   JOIN constraints c ON calc.constraints_id = c.id 
				   WHERE calc.id = $1 RETURNING id;`

	var requestID int
	err = tx.QueryRow(context.Background(), requestSQL, calculationID).Scan(&requestID)
	if err != nil {
		return fmt.Errorf("failed to insert calculation request: %v", err)
	}

	// Extract results from Python response (handle both camelCase and snake_case)
	fillRate, _ := pythonResponse["fill_rate"].(float64)
	if fillRate == 0 {
		fillRate, _ = pythonResponse["fillRate"].(float64)
	}
	totalWeight, _ := pythonResponse["total_weight"].(float64)
	if totalWeight == 0 {
		totalWeight, _ = pythonResponse["totalWeight"].(float64)
	}

	// Insert to calculation_results
	resultSQL := `INSERT INTO calculation_results (request_id, fill_rate, total_weight) VALUES ($1, $2, $3) RETURNING id;`
	var resultID int
	err = tx.QueryRow(context.Background(), resultSQL, requestID, fillRate, totalWeight).Scan(&resultID)
	if err != nil {
		return fmt.Errorf("failed to insert calculation result: %v", err)
	}

	// Parse placed items from Python response (handle both formats)
	placedItems, ok := pythonResponse["placed_items"].([]interface{})
	if !ok {
		placedItems, ok = pythonResponse["placedItems"].([]interface{})
	}

	if ok {
		for _, item := range placedItems {
			if itemData, ok := item.(map[string]interface{}); ok {
				// Try different field names for positions
				posX, _ := itemData["position_x"].(float64)
				if posX == 0 {
					posX, _ = itemData["x"].(float64)
				}
				posY, _ := itemData["position_y"].(float64)
				if posY == 0 {
					posY, _ = itemData["y"].(float64)
				}
				posZ, _ := itemData["position_z"].(float64)
				if posZ == 0 {
					posZ, _ = itemData["z"].(float64)
				}

				// For item_id, we need to find the corresponding item in database
				itemName, _ := itemData["id"].(string)
				rotation := 0 // default rotation since not provided in BLF response

				// Find item_id from database based on item name/identifier
				var itemDBID int
				findItemSQL := `SELECT id FROM items WHERE name = $1 OR name LIKE $2 LIMIT 1;`
				err = tx.QueryRow(context.Background(), findItemSQL, itemName, itemName+"%").Scan(&itemDBID)
				if err != nil {
					log.Printf("Could not find item ID for %s, skipping: %v", itemName, err)
					continue
				}

				placedItemSQL := `INSERT INTO placed_items (result_id, item_id, position_x, position_y, position_z, rotation_type) 
								  VALUES ($1, $2, $3, $4, $5, $6);`
				_, err = tx.Exec(context.Background(), placedItemSQL, resultID, itemDBID, posX, posY, posZ, rotation)
				if err != nil {
					return fmt.Errorf("failed to insert placed item: %v", err)
				}
			}
		}
	}

	return tx.Commit(context.Background())
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

		// 4. Insert Groups first (needed for item_groups reference)
		groupMap := make(map[string]int) // map group_id_string to group_id
		for _, group := range requestData.Groups {
			// First check if item_group exists, if not create it
			var itemGroupID int

			// Try to find existing item_group
			selectSQL := `SELECT id FROM item_groups WHERE name = $1;`
			err = tx.QueryRow(context.Background(), selectSQL, group.Name).Scan(&itemGroupID)
			if err != nil {
				// Item group doesn't exist, create it
				insertSQL := `INSERT INTO item_groups (name, color) VALUES ($1, $2) RETURNING id;`
				err = tx.QueryRow(context.Background(), insertSQL, group.Name, group.Color).Scan(&itemGroupID)
				if err != nil {
					log.Printf("Failed to insert item_group: %v", err)
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save item group data."})
					return
				}
			} else {
				// Item group exists, update color if different
				updateSQL := `UPDATE item_groups SET color = $2 WHERE id = $1;`
				_, err = tx.Exec(context.Background(), updateSQL, itemGroupID, group.Color)
				if err != nil {
					log.Printf("Failed to update item_group color: %v", err)
				}
			}
			groupMap[group.ID] = itemGroupID

			// Insert to groups table for backward compatibility
			groupSQL := `INSERT INTO groups (calculation_id, group_id_string, name, color) VALUES ($1, $2, $3, $4);`
			_, err = tx.Exec(context.Background(), groupSQL, calculationID, group.ID, group.Name, group.Color)
			if err != nil {
				log.Printf("Failed to insert group: %v", err)
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save group data."})
				return
			}
		}

		// 5. Insert Items with proper group references
		for _, item := range requestData.Items {
			groupID, exists := groupMap[item.Group]
			if !exists {
				groupID = 1 // default group if not found
			}

			itemSQL := `INSERT INTO items (container_id, name, width, height, length, weight, quantity, group_id) VALUES ($1, $2, $3, $4, $5, $6, $7, $8);`
			_, err = tx.Exec(context.Background(), itemSQL, containerID, item.ID, item.Width, item.Height, item.Length, item.Weight, item.Quantity, groupID)
			if err != nil {
				log.Printf("Failed to insert item: %v", err)
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save item data."})
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

		// Parse Python response to save structured data
		var pythonResponse map[string]interface{}
		err = json.Unmarshal(pythonResponseBody, &pythonResponse)
		if err != nil {
			log.Printf("Failed to parse Python response: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse calculation result."})
			return
		}

		// Save structured results to database
		err = saveCalculationResults(db, calculationID, pythonResponse)
		if err != nil {
			log.Printf("Failed to save calculation results: %v", err)
			// Don't block, just log
		}
		log.Printf("Saved structured calculation results for calculation ID: %d", calculationID)

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
		log.Fatal("JWT_SECRET_KEY environment variable is required. Please set it in your .env file or environment. It should be at least 32 characters long for security.")
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
