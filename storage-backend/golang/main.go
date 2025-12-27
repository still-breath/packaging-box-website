package main

import (
	"bufio"
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v4"
	"github.com/jackc/pgx/v4/pgxpool"
	"golang.org/x/crypto/bcrypt"
)

// --- JWT Secret ---
var jwtKey = []byte(os.Getenv("JWT_SECRET_KEY"))

// In-memory mapping from python job id -> local calculation id
var jobMap = make(map[string]int)
var jobMapMutex = &sync.Mutex{}

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
	Container    Container   `json:"container"`
	Items        []Item      `json:"items"`
	Groups       []Group     `json:"groups"`
	Algorithm    string      `json:"algorithm"`
	ActivityName string      `json:"activity_name"`
	Constraints  Constraints `json:"constraints"`
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
	var err error
	// By default do NOT drop existing tables on startup to preserve data.
	// To force a reset (for testing) set environment variable RESET_DB=true
	if os.Getenv("RESET_DB") == "true" {
		_, err := pool.Exec(context.Background(), `
			DROP TABLE IF EXISTS placed_items CASCADE;
			DROP TABLE IF EXISTS calculation_results CASCADE;
			DROP TABLE IF EXISTS calculation_requests CASCADE;
			DROP TABLE IF EXISTS groups CASCADE;
			DROP TABLE IF EXISTS items CASCADE;
			DROP TABLE IF EXISTS calculations CASCADE;
			DROP TABLE IF EXISTS constraints CASCADE;
			DROP TABLE IF EXISTS containers CASCADE;
			DROP TABLE IF EXISTS item_groups CASCADE;
			DROP TABLE IF EXISTS users CASCADE;
		`)
		if err != nil {
			log.Printf("Warning: Failed to drop tables: %v\n", err)
		} else {
			log.Println("Successfully dropped all existing tables.")
		}
	} else {
		log.Println("RESET_DB not set — skipping DROP TABLE. Existing data will be preserved.")
	}

	// Create Users Table
	createUsersTable := `
	CREATE TABLE IF NOT EXISTS users (
		id SERIAL PRIMARY KEY,
		username VARCHAR(255) UNIQUE NOT NULL,
		password_hash VARCHAR(255) NOT NULL, 
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createUsersTable)
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

	// Seed default item groups matching frontend presets (if missing)
	defaultGroups := []struct{ name, color string }{
		{"Box Rokok", "#A95E90"},
		{"Box Sparepart 1", "#6C6C9E"},
		{"Box Sparepart 2", "#3E8E7E"},
		{"Box Sparepart 3", "#E4A84F"},
		{"Box elektronik", "#D1603D"},
		{"Box Pos", "#A44A3F"},
		{"Box Kabel", "#4A442D"},
		{"Box Dispenser Air", "#5E4B56"},
	}

	for _, g := range defaultGroups {
		var exists int
		err = pool.QueryRow(context.Background(), "SELECT COUNT(*) FROM item_groups WHERE name = $1;", g.name).Scan(&exists)
		if err != nil {
			log.Printf("Failed to check existing item_group '%s': %v", g.name, err)
			continue
		}
		if exists == 0 {
			_, err := pool.Exec(context.Background(), "INSERT INTO item_groups (name, color) VALUES ($1, $2);", g.name, g.color)
			if err != nil {
				log.Printf("Failed to insert default item_group '%s': %v", g.name, err)
			}
		} else {
			// ensure color is up-to-date
			_, err := pool.Exec(context.Background(), "UPDATE item_groups SET color = $1 WHERE name = $2;", g.color, g.name)
			if err != nil {
				log.Printf("Failed to update color for item_group '%s': %v", g.name, err)
			}
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

		-- Ensure external_id column exists to store frontend item identifiers
		IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'items' AND column_name = 'external_id') THEN
			ALTER TABLE items ADD COLUMN external_id VARCHAR(255);
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
		calculation_id INTEGER REFERENCES calculations(id),
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

	// Ensure calculation_id column exists in case table was created previously
	_, err = pool.Exec(context.Background(), `ALTER TABLE calculation_requests ADD COLUMN IF NOT EXISTS calculation_id INTEGER REFERENCES calculations(id);`)
	if err != nil {
		log.Printf("Warning: failed to ensure calculation_id column on calculation_requests: %v", err)
	}

	// Create Calculation Results Table
	createCalculationResultsTable := `
	CREATE TABLE IF NOT EXISTS calculation_results (
		id SERIAL PRIMARY KEY,
		request_id INTEGER REFERENCES calculation_requests(id),
		fill_rate DECIMAL NOT NULL,
		total_weight DECIMAL NOT NULL,
		raw_payload JSONB,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createCalculationResultsTable)
	if err != nil {
		log.Fatalf("Failed to create calculation_results table: %v\n", err)
	}
	log.Println("'calculation_results' table is ready.")

	// Ensure raw_payload column exists for backward compatibility
	_, err = pool.Exec(context.Background(), `ALTER TABLE calculation_results ADD COLUMN IF NOT EXISTS raw_payload JSONB;`)
	if err != nil {
		log.Printf("Warning: failed to ensure raw_payload column on calculation_results: %v", err)
	}

	// Create Loaded Boxes Table: store references to items loaded for a result
	createLoadedBoxesTable := `
	CREATE TABLE IF NOT EXISTS loaded_boxes (
		id SERIAL PRIMARY KEY,
		result_id INTEGER REFERENCES calculation_results(id),
		item_id INTEGER REFERENCES items(id),
		item_name VARCHAR(255),
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createLoadedBoxesTable)
	if err != nil {
		log.Fatalf("Failed to create loaded_boxes table: %v\n", err)
	}
	log.Println("'loaded_boxes' table is ready.")

	// Create Placed Items Table (now references loaded_boxes)
	createPlacedItemsTable := `
	CREATE TABLE IF NOT EXISTS placed_items (
		id SERIAL PRIMARY KEY,
		result_id INTEGER REFERENCES calculation_results(id),
		item_id INTEGER REFERENCES items(id),
		loaded_box_id INTEGER REFERENCES loaded_boxes(id),
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
		activity_name VARCHAR(255),
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createCalculationsTable)
	if err != nil {
		log.Fatalf("Failed to create calculations table: %v\n", err)
	}
	log.Println("'calculations' table is ready.")

	// Ensure activity_name column exists for calculations (added later)
	_, err = pool.Exec(context.Background(), `ALTER TABLE calculations ADD COLUMN IF NOT EXISTS activity_name VARCHAR(255);`)
	if err != nil {
		log.Printf("Warning: failed to ensure activity_name column on calculations: %v", err)
	}

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

	// Create History Rows Table: a single entry representing a history row shown in UI
	createHistoryTable := `
	CREATE TABLE IF NOT EXISTS history_rows (
		id SERIAL PRIMARY KEY,
		calculation_id INTEGER,
		request_id INTEGER,
		result_id INTEGER,
		user_id INTEGER,
		algorithm VARCHAR(50),
		activity_name VARCHAR(255),
		container_id INTEGER,
		constraints_id INTEGER,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);`
	_, err = pool.Exec(context.Background(), createHistoryTable)
	if err != nil {
		log.Fatalf("Failed to create history_rows table: %v", err)
	}
	log.Println("'history_rows' table is ready.")

	// Create trigger function to remove related records when a history_rows row is deleted
	// This lets the application delete only the history row and let the DB cleanup related rows.
	createTriggerFunc := `
CREATE OR REPLACE FUNCTION delete_related_on_history_delete() RETURNS trigger AS $$
DECLARE
	cid INTEGER;
BEGIN
	-- Remove placed items and loaded boxes for any results linked to the request
	IF OLD.request_id IS NOT NULL THEN
		DELETE FROM placed_items WHERE result_id IN (SELECT id FROM calculation_results WHERE request_id = OLD.request_id);
		DELETE FROM loaded_boxes WHERE result_id IN (SELECT id FROM calculation_results WHERE request_id = OLD.request_id);
		DELETE FROM calculation_results WHERE request_id = OLD.request_id;
		DELETE FROM calculation_requests WHERE id = OLD.request_id;
	END IF;

	-- Remove groups, calculations, items and containers for the calculation
	IF OLD.calculation_id IS NOT NULL THEN
		SELECT container_id INTO cid FROM calculations WHERE id = OLD.calculation_id;
		DELETE FROM groups WHERE calculation_id = OLD.calculation_id;
		DELETE FROM calculations WHERE id = OLD.calculation_id;
		IF cid IS NOT NULL THEN
			DELETE FROM items WHERE container_id = cid;
			DELETE FROM containers WHERE id = cid;
		END IF;
	END IF;

	-- Remove constraints if present
	IF OLD.constraints_id IS NOT NULL THEN
		DELETE FROM constraints WHERE id = OLD.constraints_id;
	END IF;

	RETURN NULL;
END;
$$ LANGUAGE plpgsql;`

	_, err = pool.Exec(context.Background(), createTriggerFunc)
	if err != nil {
		log.Fatalf("Failed to create trigger function for history_rows cleanup: %v", err)
	}

	createTrigger := `
DO $$
BEGIN
	IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'history_rows_after_delete_trigger') THEN
		CREATE TRIGGER history_rows_after_delete_trigger
		AFTER DELETE ON history_rows
		FOR EACH ROW EXECUTE PROCEDURE delete_related_on_history_delete();
	END IF;
END$$;`

	_, err = pool.Exec(context.Background(), createTrigger)
	if err != nil {
		log.Fatalf("Failed to create history_rows delete trigger: %v", err)
	}
}

func migrateCalculationRequestLinks(db *pgxpool.Pool) {
	log.Println("Starting migration: populate calculation_id on calculation_requests where missing...")
	ctx := context.Background()

	rows, err := db.Query(ctx, "SELECT id, container_id, algorithm, created_at FROM calculation_requests WHERE calculation_id IS NULL;")
	if err != nil {
		log.Printf("Migration query failed: %v", err)
		return
	}
	defer rows.Close()

	var processed, updated, skipped int
	for rows.Next() {
		var reqID int
		var containerID sql.NullInt32
		var algorithm string
		var createdAt time.Time
		if err := rows.Scan(&reqID, &containerID, &algorithm, &createdAt); err != nil {
			log.Printf("Failed to scan calculation_requests row: %v", err)
			continue
		}
		processed++
		if !containerID.Valid {
			skipped++
			continue
		}

		// compute a 5-minute window around createdAt in Go to avoid SQL type/operator issues
		startWindow := createdAt.Add(-5 * time.Minute)
		endWindow := createdAt.Add(5 * time.Minute)
		candidateRows, cerr := db.Query(ctx, "SELECT id, created_at FROM calculations WHERE container_id=$1 AND algorithm=$2 AND created_at BETWEEN $3 AND $4;", int(containerID.Int32), algorithm, startWindow, endWindow)
		if cerr != nil {
			log.Printf("Failed to query candidate calculations for request %d: %v", reqID, cerr)
			skipped++
			continue
		}
		var candidates []struct {
			id int
			ts time.Time
		}
		for candidateRows.Next() {
			var cid int
			var cts time.Time
			if err := candidateRows.Scan(&cid, &cts); err == nil {
				candidates = append(candidates, struct {
					id int
					ts time.Time
				}{cid, cts})
			}
		}
		candidateRows.Close()

		if len(candidates) == 1 {
			// update request row
			if _, uerr := db.Exec(ctx, "UPDATE calculation_requests SET calculation_id=$1 WHERE id=$2;", candidates[0].id, reqID); uerr != nil {
				log.Printf("Failed to update calculation_request %d -> calculation_id %d: %v", reqID, candidates[0].id, uerr)
				skipped++
			} else {
				updated++
			}
		} else if len(candidates) > 1 {
			var bestID int
			bestDiff := time.Hour * 24 * 365
			tie := false
			for _, cand := range candidates {
				diff := cand.ts.Sub(createdAt)
				if diff < 0 {
					diff = -diff
				}
				if diff < bestDiff {
					bestDiff = diff
					bestID = cand.id
					tie = false
				} else if diff == bestDiff {
					tie = true
				}
			}
			if tie || bestID == 0 {
				skipped++
			} else {
				if _, uerr := db.Exec(ctx, "UPDATE calculation_requests SET calculation_id=$1 WHERE id=$2;", bestID, reqID); uerr != nil {
					log.Printf("Failed to update calculation_request %d -> calculation_id %d: %v", reqID, bestID, uerr)
					skipped++
				} else {
					updated++
				}
			}
		} else {
			skipped++
		}
	}

	log.Printf("Migration finished: processed=%d updated=%d skipped=%d", processed, updated, skipped)
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
	// Also store calculation_id to create a deterministic mapping between calculation and request
	requestSQL := `INSERT INTO calculation_requests (user_id, container_id, algorithm, enforce_load_capacity, enforce_stacking, enforce_priority, enforce_lifo, calculation_id) 
				   SELECT user_id, container_id, algorithm, c.enforce_load_capacity, c.enforce_stacking, c.enforce_priority, c.enforce_lifo, calc.id 
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

	// Marshal raw payload to store it verbatim (preserve camelCase result payload)
	rawPayloadBytes, _ := json.Marshal(pythonResponse)

	// Insert to calculation_results (store raw payload JSONB for exact replay)
	resultSQL := `INSERT INTO calculation_results (request_id, fill_rate, total_weight, raw_payload) VALUES ($1, $2, $3, $4) RETURNING id;`
	var resultID int
	err = tx.QueryRow(context.Background(), resultSQL, requestID, fillRate, totalWeight, rawPayloadBytes).Scan(&resultID)
	if err != nil {
		return fmt.Errorf("failed to insert calculation result: %v", err)
	}

	// Record an entry in history_rows so the UI has a single row to reference.
	// Also used by DB trigger to cascade deletes when a history row is removed.
	var userID int
	var containerID sql.NullInt32
	var constraintsID sql.NullInt32
	var algorithm string
	var activityName sql.NullString
	// fetch calculation metadata
	err = tx.QueryRow(context.Background(), "SELECT user_id, container_id, constraints_id, algorithm, activity_name FROM calculations WHERE id=$1;", calculationID).Scan(&userID, &containerID, &constraintsID, &algorithm, &activityName)
	if err == nil {
		insertHistorySQL := `INSERT INTO history_rows (calculation_id, request_id, result_id, user_id, algorithm, activity_name, container_id, constraints_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8);`
		_, _ = tx.Exec(context.Background(), insertHistorySQL, calculationID, requestID, resultID, userID, algorithm, activityName, containerID, constraintsID)
	} else {
		log.Printf("Warning: could not populate history_rows metadata for calculation %d: %v", calculationID, err)
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

				var itemDBID int
				var findErr error
				baseName := itemName
				if idx := strings.Index(itemName, "_"); idx != -1 {
					baseName = itemName[:idx]
				}

				queries := []struct {
					sql  string
					args []interface{}
				}{
					{"SELECT id FROM items WHERE external_id = $1 LIMIT 1;", []interface{}{itemName}},
					{"SELECT id FROM items WHERE external_id ILIKE $1 LIMIT 1;", []interface{}{baseName}},
					{"SELECT id FROM items WHERE name = $1 LIMIT 1;", []interface{}{itemName}},
					{"SELECT id FROM items WHERE name = $1 LIMIT 1;", []interface{}{baseName}},
				}
				found := false
				for _, q := range queries {
					findErr = tx.QueryRow(context.Background(), q.sql, q.args...).Scan(&itemDBID)
					if findErr == nil {
						found = true
						break
					}
				}
				if !found {
					log.Printf("Could not find item ID for %s, skipping placed item to avoid mismatch", itemName)
					continue
				}

				// Insert a loaded_box record referencing the existing item (no duplicate item properties)
				var loadedBoxID int
				loadedBoxSQL := `INSERT INTO loaded_boxes (result_id, item_id, item_name) VALUES ($1, $2, $3) RETURNING id;`
				if err := tx.QueryRow(context.Background(), loadedBoxSQL, resultID, itemDBID, itemName).Scan(&loadedBoxID); err != nil {
					log.Printf("Failed to insert loaded_box for item %s (id %d): %v", itemName, itemDBID, err)
					continue
				}

				placedItemSQL := `INSERT INTO placed_items (result_id, item_id, loaded_box_id, position_x, position_y, position_z, rotation_type) 
								  VALUES ($1, $2, $3, $4, $5, $6, $7);`
				_, err = tx.Exec(context.Background(), placedItemSQL, resultID, itemDBID, loadedBoxID, posX, posY, posZ, rotation)
				if err != nil {
					return fmt.Errorf("failed to insert placed item: %v", err)
				}
			}
		}
	}

	return tx.Commit(context.Background())
}

// --- Stream proxy handler: forwards SSE from Python and saves final result ---
func handleGoStreamProxy(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		jobID := c.Param("job_id")

		jobMapMutex.Lock()
		calcID, ok := jobMap[jobID]
		jobMapMutex.Unlock()
		if !ok {
			c.JSON(http.StatusNotFound, gin.H{"error": "Job not found"})
			return
		}

		pythonBase := os.Getenv("PYTHON_BACKEND_URL")
		// default Python stream URL if not provided
		var pythonStreamURL string
		if pythonBase == "" {
			pythonStreamURL = fmt.Sprintf("http://localhost:8000/calculate/stream/%s", jobID)
		} else {
			// If PYTHON_BACKEND_URL points to /calculate/python, derive base
			base := strings.TrimSuffix(pythonBase, "/calculate/python")
			base = strings.TrimSuffix(base, "/calculate")
			pythonStreamURL = fmt.Sprintf("%s/calculate/stream/%s", base, jobID)
		}

		req, _ := http.NewRequest("GET", pythonStreamURL, nil)
		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			log.Printf("Failed to connect to Python SSE: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to connect to Python stream"})
			return
		}
		// Do not defer resp.Body.Close() here because we will stream until done

		c.Writer.Header().Set("Content-Type", "text/event-stream")
		c.Writer.Header().Set("Cache-Control", "no-cache")
		c.Writer.Header().Set("Connection", "keep-alive")
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Status(http.StatusOK)

		flusher, okf := c.Writer.(http.Flusher)
		if !okf {
			resp.Body.Close()
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Streaming unsupported"})
			return
		}

		reader := bufio.NewReader(resp.Body)
		expectingDone := false
		var doneBuilder strings.Builder

		for {
			line, err := reader.ReadString('\n')
			if err != nil && err != io.EOF {
				log.Printf("Error reading from Python SSE body: %v", err)
				break
			}

			// Remove trailing \n and any \r
			trimmed := strings.TrimRight(line, "\r\n")

			// Forward line to client immediately
			_, _ = c.Writer.Write([]byte(trimmed + "\n"))
			flusher.Flush()

			if strings.HasPrefix(trimmed, "event: done") {
				expectingDone = true
				doneBuilder.Reset()
				// continue to next lines which may contain one or more data: lines
				continue
			}

			if expectingDone {
				// accumulate all consecutive data: lines until a blank line indicates end of event
				if strings.HasPrefix(trimmed, "data:") {
					data := strings.TrimPrefix(trimmed, "data: ")
					doneBuilder.WriteString(data)
					// continue reading more lines to collect full payload
					continue
				}

				// blank line (or any non-data line) after collecting data indicates end of event
				if strings.TrimSpace(trimmed) == "" {
					// parse JSON and save to DB
					var pythonResponse map[string]interface{}
					if err := json.Unmarshal([]byte(doneBuilder.String()), &pythonResponse); err != nil {
						log.Printf("Failed to parse final python result: %v", err)
					} else {
						if err := saveCalculationResults(db, calcID, pythonResponse); err != nil {
							log.Printf("Failed to save calculation results (proxy): %v", err)
						} else {
							log.Printf("Saved structured calculation results for calculation ID: %d (via proxy)", calcID)
						}
					}

					// after handling done, break and close stream
					break
				}

				// If we get here and the line is neither data: nor blank, treat as end and attempt parse
				var pythonResponse map[string]interface{}
				if doneBuilder.Len() > 0 {
					if err := json.Unmarshal([]byte(doneBuilder.String()), &pythonResponse); err != nil {
						log.Printf("Failed to parse final python result (unexpected line): %v", err)
					} else {
						if err := saveCalculationResults(db, calcID, pythonResponse); err != nil {
							log.Printf("Failed to save calculation results (proxy): %v", err)
						} else {
							log.Printf("Saved structured calculation results for calculation ID: %d (via proxy)", calcID)
						}
					}
				}
				break
			}

			if err == io.EOF {
				// End of stream
				break
			}
		}

		resp.Body.Close()
		return
	}
}

func handleGoCancel(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		var payload struct {
			JobID string `json:"job_id"`
		}
		if err := c.ShouldBindJSON(&payload); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
			return
		}
		if payload.JobID == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "job_id is required"})
			return
		}

		pythonBase := os.Getenv("PYTHON_BACKEND_URL")
		var cancelURL string
		if pythonBase == "" {
			cancelURL = fmt.Sprintf("http://localhost:8000/calculate/stream/%s/cancel", payload.JobID)
		} else {
			base := strings.TrimSuffix(pythonBase, "/calculate/python")
			base = strings.TrimSuffix(base, "/calculate")
			cancelURL = fmt.Sprintf("%s/calculate/stream/%s/cancel", base, payload.JobID)
		}

		resp, err := http.Post(cancelURL, "application/json", nil)
		if err != nil {
			log.Printf("Failed to call Python cancel endpoint: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to cancel job"})
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode >= 400 {
			body, _ := io.ReadAll(resp.Body)
			log.Printf("Python cancel returned error: %s", string(body))
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Python cancel failed"})
			return
		}

		// Also remove mapping if exists
		jobMapMutex.Lock()
		delete(jobMap, payload.JobID)
		jobMapMutex.Unlock()

		c.JSON(http.StatusOK, gin.H{"status": "cancelled"})
	}
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

		// Verify user exists in database
		var existsUser bool
		err := db.QueryRow(context.Background(), "SELECT EXISTS(SELECT 1 FROM users WHERE id=$1)", userID).Scan(&existsUser)
		if err != nil || !existsUser {
			log.Printf("User ID %d does not exist in database: %v", userID, err)
			c.JSON(http.StatusUnauthorized, gin.H{"error": "User not found"})
			return
		} // Use a transaction to ensure all inserts succeed or none do
		tx, err := db.Begin(context.Background())
		if err != nil {
			log.Printf("Failed to begin transaction: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to start database transaction."})
			return
		}
		defer func() {
			if tx != nil {
				_ = tx.Rollback(context.Background()) // ignore error: tx may be already committed
			}
		}()

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

		algorithm := requestData.Algorithm
		if algorithm == "golang" {
			algorithm = "PYTHON_BLF"
		}

		// 3. Insert Calculation (include optional activity_name)
		var calculationID int
		calculationSQL := `INSERT INTO calculations (user_id, container_id, constraints_id, algorithm, activity_name) VALUES ($1, $2, $3, $4, $5) RETURNING id;`
		err = tx.QueryRow(context.Background(), calculationSQL, userID, containerID, constraintsID, algorithm, requestData.ActivityName).Scan(&calculationID)
		if err != nil {
			log.Printf("Failed to insert calculation: %v, userID: %d, containerID: %d, constraintsID: %d", err, userID, containerID, constraintsID)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save calculation data."})
			return
		}

		// 4. Insert Groups first (needed for item_groups reference)
		groupMap := make(map[string]int)        // map group_id_string to group_id
		groupNameMap := make(map[string]string) // map group_id_string to display name
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
			// map both by frontend id and by name so items referencing either will resolve
			groupMap[group.ID] = itemGroupID
			groupMap[group.Name] = itemGroupID
			// store display name for both keys so item insertion can use the group name
			groupNameMap[group.ID] = group.Name
			groupNameMap[group.Name] = group.Name

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
				// try to find item_group by name in DB
				var foundID int
				err = tx.QueryRow(context.Background(), `SELECT id FROM item_groups WHERE name=$1;`, item.Group).Scan(&foundID)
				if err != nil {
					// not found: create a new item_group for this name to satisfy FK
					insertSQL := `INSERT INTO item_groups (name, color) VALUES ($1, $2) RETURNING id;`
					if insertErr := tx.QueryRow(context.Background(), insertSQL, item.Group, "#CCCCCC").Scan(&foundID); insertErr != nil {
						log.Printf("Failed to create fallback item_group for %s: %v", item.Group, insertErr)
						c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save item group for item."})
						return
					}
					// record display name for this created group
					groupNameMap[item.Group] = item.Group
				}
				groupID = foundID
				// cache mapping for subsequent items
				groupMap[item.Group] = groupID
			}

			// determine display name for this item's group from item_groups table if possible
			var displayName string
			if dn, ok := groupNameMap[item.Group]; ok && dn != "" {
				displayName = dn
			} else {
				// fallback: fetch from DB by groupID
				_ = tx.QueryRow(context.Background(), `SELECT name FROM item_groups WHERE id=$1 LIMIT 1;`, groupID).Scan(&displayName)
				if displayName == "" {
					displayName = item.Group // final fallback
				}
			}

			itemSQL := `INSERT INTO items (container_id, name, width, height, length, weight, quantity, group_id, external_id) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);`
			_, err = tx.Exec(context.Background(), itemSQL, containerID, displayName, item.Width, item.Height, item.Length, item.Weight, item.Quantity, groupID, item.ID)
			if err != nil {
				log.Printf("Failed to insert item: %v", err)
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save item data."})
				return
			}
		}

		// Use the mapped algorithm for Python backend call
		requestData.Algorithm = algorithm

		log.Printf("Saved new calculation with ID: %d for user ID: %d", calculationID, userID)

		// Commit the transaction so other transactions can see the inserted rows
		if err := tx.Commit(context.Background()); err != nil {
			log.Printf("Failed to commit transaction before calling python backend: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to commit calculation transaction."})
			return
		}
		// mark tx nil so deferred rollback is no-op
		tx = nil

		// --- Call Python Backend (supports streaming GA jobs) ---
		pythonURL := os.Getenv("PYTHON_BACKEND_URL")
		if pythonURL == "" {
			pythonURL = "http://localhost:8000/calculate/python"
		}
		jsonReq, _ := json.Marshal(requestData)

		if algorithm == "PYTHON_GA" || algorithm == "PYTHON_CLPTAC" {
			// Start streamed GA job on Python and return job_id to client
			streamStart := os.Getenv("PYTHON_BACKEND_STREAM_START")
			if streamStart == "" {
				base := strings.TrimSuffix(pythonURL, "/calculate/python")
				base = strings.TrimSuffix(base, "/calculate")
				streamStart = fmt.Sprintf("%s/calculate/stream/start", base)
			}

			resp2, err := http.Post(streamStart, "application/json", bytes.NewBuffer(jsonReq))
			if err != nil {
				log.Printf("Failed to start Python GA job: %v", err)
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to start GA job."})
				return
			}
			defer resp2.Body.Close()

			body2, err := io.ReadAll(resp2.Body)
			if err != nil {
				log.Printf("Failed to read start response: %v", err)
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to start GA job."})
				return
			}

			var startResp map[string]interface{}
			if err := json.Unmarshal(body2, &startResp); err != nil {
				log.Printf("Invalid start response from Python: %v", err)
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Invalid start response from GA service."})
				return
			}
			jobID, _ := startResp["job_id"].(string)
			if jobID == "" {
				log.Printf("Python did not return job_id: %s", string(body2))
				c.JSON(http.StatusInternalServerError, gin.H{"error": "GA service failed to return job id."})
				return
			}

			// Map python job id to our calculationID so proxy can save result
			jobMapMutex.Lock()
			jobMap[jobID] = calculationID
			jobMapMutex.Unlock()

			// Return job id to client
			c.JSON(http.StatusOK, gin.H{"job_id": jobID})
			return
		}

		// Fallback synchronous call for non-GA algorithms
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

// --- Calculation inspection endpoints ---

func handleListCalculations(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		userIDVal, exists := c.Get("user_id")
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
			return
		}
		userID := userIDVal.(int)

		rows, err := db.Query(context.Background(), "SELECT id, algorithm, activity_name, created_at FROM calculations WHERE user_id=$1 ORDER BY created_at DESC LIMIT 200;", userID)
		if err != nil {
			log.Printf("Failed to query calculations: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load calculations"})
			return
		}
		defer rows.Close()

		var out []gin.H
		for rows.Next() {
			var id int
			var algorithm string
			var activityName sql.NullString
			var createdAt time.Time
			if err := rows.Scan(&id, &algorithm, &activityName, &createdAt); err != nil {
				log.Printf("Failed to scan calculation row: %v", err)
				continue
			}
			item := gin.H{"id": id, "algorithm": algorithm, "created_at": createdAt}
			if activityName.Valid {
				item["activity_name"] = activityName.String
			}
			out = append(out, item)
		}
		c.JSON(http.StatusOK, out)
	}
}

func handleGetCalculation(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		userIDVal, exists := c.Get("user_id")
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
			return
		}
		userID := userIDVal.(int)

		calcID := c.Param("id")

		// Fetch calculation meta
		var calculation struct {
			ID            int
			UserID        int
			ContainerID   int
			ConstraintsID int
			Algorithm     string
			ActivityName  sql.NullString
			CreatedAt     time.Time
		}
		err := db.QueryRow(context.Background(), "SELECT id, user_id, container_id, constraints_id, algorithm, activity_name, created_at FROM calculations WHERE id=$1;", calcID).Scan(&calculation.ID, &calculation.UserID, &calculation.ContainerID, &calculation.ConstraintsID, &calculation.Algorithm, &calculation.ActivityName, &calculation.CreatedAt)
		if err != nil {
			log.Printf("Failed to fetch calculation %s: %v", calcID, err)
			c.JSON(http.StatusNotFound, gin.H{"error": "Calculation not found"})
			return
		}
		if calculation.UserID != userID {
			c.JSON(http.StatusForbidden, gin.H{"error": "Not allowed"})
			return
		}

		// Fetch container
		var container gin.H
		var cWidth, cHeight, cLength, cMaxWeight float64
		err = db.QueryRow(context.Background(), "SELECT width, height, length, max_weight FROM containers WHERE id=$1;", calculation.ContainerID).Scan(&cWidth, &cHeight, &cLength, &cMaxWeight)
		if err != nil {
			// container may be missing; continue but warn
			container = gin.H{"error": "container not found"}
		} else {
			container = gin.H{"width": cWidth, "height": cHeight, "length": cLength, "max_weight": cMaxWeight}
		}

		// Fetch constraints
		var constraints gin.H
		var enforceLifo, enforcePriority, enforceStacking, enforceLoadCapacity bool
		err = db.QueryRow(context.Background(), "SELECT enforce_lifo, enforce_priority, enforce_stacking, enforce_load_capacity FROM constraints WHERE id=$1;", calculation.ConstraintsID).Scan(&enforceLifo, &enforcePriority, &enforceStacking, &enforceLoadCapacity)
		if err != nil {
			constraints = gin.H{"error": "constraints not found"}
		} else {
			constraints = gin.H{"enforce_lifo": enforceLifo, "enforce_priority": enforcePriority, "enforce_stacking": enforceStacking, "enforce_load_capacity": enforceLoadCapacity}
		}

		// Fetch snapshot groups for this calculation
		grows, err := db.Query(context.Background(), "SELECT group_id_string, name, color FROM groups WHERE calculation_id=$1;", calcID)
		var snapGroups []gin.H
		if err == nil {
			defer grows.Close()
			for grows.Next() {
				var gid, name, color string
				if err := grows.Scan(&gid, &name, &color); err != nil {
					continue
				}
				snapGroups = append(snapGroups, gin.H{"group_id_string": gid, "name": name, "color": color})
			}
		}

		// Fetch items for the container
		irows, err := db.Query(context.Background(), `SELECT i.id, i.name, i.width, i.height, i.length, i.weight, i.quantity, ig.id AS group_id, ig.name AS group_name, ig.color AS group_color
			FROM items i LEFT JOIN item_groups ig ON i.group_id = ig.id WHERE i.container_id = $1;`, calculation.ContainerID)
		var items []gin.H
		if err == nil {
			defer irows.Close()
			for irows.Next() {
				var id int
				var name string
				var width, height, lengthd, weight float64
				var quantity int
				var groupID sql.NullInt32
				var groupName, groupColor sql.NullString
				if err := irows.Scan(&id, &name, &width, &height, &lengthd, &weight, &quantity, &groupID, &groupName, &groupColor); err != nil {
					continue
				}
				it := gin.H{"id": id, "name": name, "width": width, "height": height, "length": lengthd, "weight": weight, "quantity": quantity}
				if groupID.Valid {
					it["group"] = gin.H{"id": int(groupID.Int32), "name": groupName.String, "color": groupColor.String}
				}
				items = append(items, it)
			}
		}

		// Attempt to locate a calculation_results row related to this calculation.
		// First try a direct mapping via calculation_requests.calculation_id for deterministic lookup.
		// Fallback to a time-window-based lookup for older DB rows that may not have calculation_id populated.
		var result gin.H
		var reqID int
		// try direct mapping
		err = db.QueryRow(context.Background(), "SELECT id FROM calculation_requests WHERE calculation_id=$1 LIMIT 1;", calculation.ID).Scan(&reqID)
		if err != nil {
			// fallback: Prefer requests created around the same time as the calculation to avoid picking an unrelated recent request
			// compute window in Go to avoid SQL operator/type issues
			startWindow := calculation.CreatedAt.Add(-5 * time.Minute)
			endWindow := calculation.CreatedAt.Add(5 * time.Minute)
			err = db.QueryRow(context.Background(), "SELECT id FROM calculation_requests WHERE container_id=$1 AND algorithm=$2 AND created_at BETWEEN $3 AND $4 ORDER BY created_at DESC LIMIT 1;", calculation.ContainerID, calculation.Algorithm, startWindow, endWindow).Scan(&reqID)
		}
		if err == nil {
			// fetch result (also try to read raw_payload if available)
			var resID int
			var fillRate, totalWeight float64
			var rawPayloadBytes []byte
			rerr := db.QueryRow(context.Background(), "SELECT id, fill_rate, total_weight, raw_payload FROM calculation_results WHERE request_id=$1 LIMIT 1;", reqID).Scan(&resID, &fillRate, &totalWeight, &rawPayloadBytes)
			if rerr == nil {
				// If raw payload present, prefer to use it to construct the returned result (but keep snake_case keys expected by frontend)
				if len(rawPayloadBytes) > 0 {
					var payload map[string]interface{}
					if err := json.Unmarshal(rawPayloadBytes, &payload); err == nil {
						// Build placed_items in snake_case to remain compatible with frontend history view
						var placedItems []gin.H
						if pitems, ok := payload["placedItems"].([]interface{}); ok {
							for _, pi := range pitems {
								if imap, ok := pi.(map[string]interface{}); ok {
									ci := gin.H{"id": imap["id"], "x": imap["x"], "y": imap["y"], "z": imap["z"], "length": imap["length"], "width": imap["width"], "height": imap["height"], "weight": imap["weight"]}
									// rotation field fallback handling
									if rot, ok := imap["rotation"].(float64); ok {
										ci["rotation"] = int(rot)
									} else if rot2, ok := imap["rotation_type"].(float64); ok {
										ci["rotation"] = int(rot2)
									}
									if color, ok := imap["color"].(string); ok {
										ci["color"] = color
									}
									placedItems = append(placedItems, ci)
								}
							}
						}

						// fill and weight from payload if present
						fr := fillRate
						if f, ok := payload["fillRate"].(float64); ok && f != 0 {
							fr = f
						}
						tw := totalWeight
						if t, ok := payload["totalWeight"].(float64); ok && t != 0 {
							tw = t
						}

						result = gin.H{"id": resID, "fill_rate": fr, "total_weight": tw, "placed_items": placedItems}
					} else {
						// JSON unmarshal failed, fallback to stored numeric fields and DB placed_items
						// fetch placed items details from DB
						var placedItems []gin.H
						prows, perr := db.Query(context.Background(), `SELECT lb.item_name, pi.position_x, pi.position_y, pi.position_z, pi.rotation_type, i.length, i.width, i.height, i.weight, ig.color
										FROM placed_items pi
										JOIN loaded_boxes lb ON lb.id = pi.loaded_box_id
										LEFT JOIN items i ON i.id = pi.item_id
										LEFT JOIN item_groups ig ON i.group_id = ig.id
										WHERE pi.result_id=$1;`, resID)
						if perr == nil {
							defer prows.Close()
							for prows.Next() {
								var itemName string
								var posX, posY, posZ float64
								var rotation int
								var lengthd, widthd, heightd, weight float64
								var color sql.NullString
								if err := prows.Scan(&itemName, &posX, &posY, &posZ, &rotation, &lengthd, &widthd, &heightd, &weight, &color); err != nil {
									log.Printf("Failed to scan placed item row: %v", err)
									continue
								}
								ci := gin.H{"id": itemName, "x": posX, "y": posY, "z": posZ, "rotation": rotation, "length": lengthd, "width": widthd, "height": heightd, "weight": weight}
								if color.Valid {
									ci["color"] = color.String
								}
								placedItems = append(placedItems, ci)
							}
						}
						result = gin.H{"id": resID, "fill_rate": fillRate, "total_weight": totalWeight, "placed_items": placedItems}
					}
				} else {
					// No raw payload: fallback to stored numeric fields and DB placed_items
					var placedItems []gin.H
					prows, perr := db.Query(context.Background(), `SELECT lb.item_name, pi.position_x, pi.position_y, pi.position_z, pi.rotation_type, i.length, i.width, i.height, i.weight, ig.color
										FROM placed_items pi
										JOIN loaded_boxes lb ON lb.id = pi.loaded_box_id
										LEFT JOIN items i ON i.id = pi.item_id
										LEFT JOIN item_groups ig ON i.group_id = ig.id
										WHERE pi.result_id=$1;`, resID)
					if perr == nil {
						defer prows.Close()
						for prows.Next() {
							var itemName string
							var posX, posY, posZ float64
							var rotation int
							var lengthd, widthd, heightd, weight float64
							var color sql.NullString
							if err := prows.Scan(&itemName, &posX, &posY, &posZ, &rotation, &lengthd, &widthd, &heightd, &weight, &color); err != nil {
								log.Printf("Failed to scan placed item row: %v", err)
								continue
							}
							ci := gin.H{"id": itemName, "x": posX, "y": posY, "z": posZ, "rotation": rotation, "length": lengthd, "width": widthd, "height": heightd, "weight": weight}
							if color.Valid {
								ci["color"] = color.String
							}
							placedItems = append(placedItems, ci)
						}
					}
					result = gin.H{"id": resID, "fill_rate": fillRate, "total_weight": totalWeight, "placed_items": placedItems}
				}
			}
		}

		c.JSON(http.StatusOK, gin.H{"calculation": gin.H{"id": calculation.ID, "algorithm": calculation.Algorithm, "created_at": calculation.CreatedAt}, "container": container, "constraints": constraints, "groups": snapGroups, "items": items, "result": result})
	}
}

// Delete a calculation and most related records (if owned by user)
func handleDeleteCalculation(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		userIDVal, exists := c.Get("user_id")
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
			return
		}
		userID := userIDVal.(int)

		calcIDParam := c.Param("id")

		// Fetch calculation row
		var dbUserID int
		var containerID sql.NullInt32
		var constraintsID sql.NullInt32
		var algorithm string
		var createdAt time.Time
		err := db.QueryRow(context.Background(), "SELECT id, user_id, container_id, constraints_id, algorithm, created_at FROM calculations WHERE id=$1;", calcIDParam).Scan(new(int), &dbUserID, &containerID, &constraintsID, &algorithm, &createdAt)
		if err != nil {
			log.Printf("Failed to fetch calculation %s for delete: %v", calcIDParam, err)
			c.JSON(http.StatusNotFound, gin.H{"error": "Calculation not found"})
			return
		}
		if dbUserID != userID {
			c.JSON(http.StatusForbidden, gin.H{"error": "Not allowed"})
			return
		}

		// Simplified delete flow: delete the single history row. A DB trigger will
		// cascade-cleanup related rows (placed_items, loaded_boxes, calculation_results,
		// calculation_requests, calculations, items, containers, constraints).
		tx, err := db.Begin(context.Background())
		if err != nil {
			log.Printf("Failed to begin tx for delete calculation: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete calculation"})
			return
		}
		defer func() {
			if tx != nil {
				_ = tx.Rollback(context.Background())
			}
		}()

		ct, err := tx.Exec(context.Background(), "DELETE FROM history_rows WHERE calculation_id=$1;", calcIDParam)
		if err != nil {
			log.Printf("Failed to delete history row for calculation %s: %v", calcIDParam, err)
			_ = tx.Rollback(context.Background())
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete calculation", "details": []string{err.Error()}})
			return
		}
		if ct.RowsAffected() == 0 {
			// No history row existed — nothing to delete via simplified path
			_ = tx.Rollback(context.Background())
			c.JSON(http.StatusNotFound, gin.H{"error": "History row not found"})
			return
		}

		if err := tx.Commit(context.Background()); err != nil {
			log.Printf("Failed to commit delete transaction for calc %s: %v", calcIDParam, err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete calculation", "details": []string{err.Error()}})
			return
		}
		tx = nil

		c.JSON(http.StatusOK, gin.H{"status": "deleted"})
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

// --- Item Groups Handlers ---

type createGroupRequest struct {
	Name  string `json:"name"`
	Color string `json:"color"`
}

func handleGetItemGroups(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		rows, err := db.Query(context.Background(), "SELECT id, name, color FROM item_groups ORDER BY id;")
		if err != nil {
			log.Printf("Failed to query item_groups: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load item groups"})
			return
		}
		defer rows.Close()

		var groups []gin.H
		for rows.Next() {
			var id int
			var name, color string
			if err := rows.Scan(&id, &name, &color); err != nil {
				log.Printf("Failed to scan item_group row: %v", err)
				continue
			}
			groups = append(groups, gin.H{"id": id, "name": name, "color": color})
		}
		c.JSON(http.StatusOK, groups)
	}
}

func handleCreateItemGroup(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req createGroupRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
			return
		}
		var newID int
		err := db.QueryRow(context.Background(), "INSERT INTO item_groups (name, color) VALUES ($1, $2) RETURNING id;", req.Name, req.Color).Scan(&newID)
		if err != nil {
			log.Printf("Failed to insert item_group: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create item group"})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"id": newID, "name": req.Name, "color": req.Color})
	}
}

func handleUpdateItemGroup(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		idParam := c.Param("id")
		// ensure id is an integer
		idInt, err := strconv.Atoi(idParam)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid group id"})
			return
		}
		var req createGroupRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
			return
		}
		cmdTag, err := db.Exec(context.Background(), "UPDATE item_groups SET name=$1, color=$2 WHERE id=$3;", req.Name, req.Color, idInt)
		if err != nil {
			log.Printf("Failed to update item_group %s: %v", idParam, err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update item group"})
			return
		}
		if cmdTag.RowsAffected() == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "Item group not found"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"id": idParam, "name": req.Name, "color": req.Color})
	}
}

func handleDeleteItemGroup(db *pgxpool.Pool) gin.HandlerFunc {
	return func(c *gin.Context) {
		idParam := c.Param("id")
		// ensure id is an integer
		idInt, err := strconv.Atoi(idParam)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid group id"})
			return
		}

		// Use a transaction: clear references in items, then delete the group
		tx, err := db.Begin(context.Background())
		if err != nil {
			log.Printf("Failed to begin tx for deleting item_group %d: %v", idInt, err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete item group"})
			return
		}
		defer func() {
			_ = tx.Rollback(context.Background())
		}()

		// unset group references on items
		if _, err := tx.Exec(context.Background(), "UPDATE items SET group_id = NULL WHERE group_id = $1;", idInt); err != nil {
			log.Printf("Failed to clear item references for item_group %d: %v", idInt, err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete item group"})
			return
		}

		// delete the group
		cmdTag, err := tx.Exec(context.Background(), "DELETE FROM item_groups WHERE id=$1;", idInt)
		if err != nil {
			log.Printf("Failed to delete item_group %d: %v", idInt, err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete item group"})
			return
		}
		if cmdTag.RowsAffected() == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "Item group not found"})
			return
		}

		if err := tx.Commit(context.Background()); err != nil {
			log.Printf("Failed to commit tx deleting item_group %d: %v", idInt, err)
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete item group"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"status": "deleted"})
	}
}

func main() {
	if os.Getenv("JWT_SECRET_KEY") == "" {
		log.Fatal("JWT_SECRET_KEY environment variable is required. Please set it in your .env file or environment. It should be at least 32 characters long for security.")
	}

	dbPool := connectDB()
	defer dbPool.Close()

	setupDatabase(dbPool)
	// Run migration to populate calculation_id for older calculation_requests
	migrateCalculationRequestLinks(dbPool)

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
		apiRoutes.POST("/calculate/golang/cancel", handleGoCancel(dbPool))
		// Item groups CRUD
		apiRoutes.GET("/item-groups", handleGetItemGroups(dbPool))
		apiRoutes.POST("/item-groups", handleCreateItemGroup(dbPool))
		apiRoutes.PUT("/item-groups/:id", handleUpdateItemGroup(dbPool))
		apiRoutes.DELETE("/item-groups/:id", handleDeleteItemGroup(dbPool))
		// Calculation inspection
		apiRoutes.GET("/calculations", handleListCalculations(dbPool))
		apiRoutes.GET("/calculations/:id", handleGetCalculation(dbPool))
		apiRoutes.DELETE("/calculations/:id", handleDeleteCalculation(dbPool))
	}

	router.GET("/api/calculate/golang/stream/:job_id", handleGoStreamProxy(dbPool))

	log.Println("Go server starting on port 8080...")
	router.Run(":8080")
}
