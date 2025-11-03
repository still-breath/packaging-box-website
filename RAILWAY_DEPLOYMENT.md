# Railway Deployment Configuration
# Deploy ke Railway: https://railway.app

# Konfigurasi layanan di railway.json
# Setiap service harus memiliki Dockerfile di direktorinya

# Untuk deployment:
# 1. Connect GitHub repository ke Railway
# 2. Railway akan auto-detect Dockerfile
# 3. Set environment variables di Railway dashboard
# 4. Auto-deploy pada setiap push ke main branch

# Services yang akan di-deploy:
# - PostgreSQL (managed service)
# - Go Backend (port 8080)
# - Python Backend (port 8000)
# - React Frontend (port 3000)

# Required Environment Variables di Railway:
# POSTGRES_DB=packaging_db
# POSTGRES_USER=your_username
# POSTGRES_PASSWORD=your_secure_password
# JWT_SECRET_KEY=your_jwt_secret_key
# PYTHON_SECRET_KEY=your_python_secret_key

# Konfigurasi build command
build: |
  # Go backend
  cd storage-backend/golang
  go build -o main .
  
  # Python backend
  cd ../python
  pip install -r requirements.txt
  
  # React frontend
  cd ../../storage-manager
  npm ci
  npm run build

# Konfigurasi start command untuk setiap service
# Go backend: ./storage-backend/golang/main
# Python backend: cd storage-backend/python && uvicorn main:app --host 0.0.0.0 --port 8000
# Frontend: cd storage-manager && npm start