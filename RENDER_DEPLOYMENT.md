# Render Deployment Configuration
# Deploy ke Render: https://render.com

## Setup Render Services

### 1. PostgreSQL Database
- Service Type: PostgreSQL
- Name: packaging-db
- Region: Singapore (or closest to you)
- Version: 13
- Auto-backup: Enable

### 2. Python Backend
- Service Type: Web Service
- Build Command: `pip install -r requirements.txt`
- Start Command: `cd storage-backend/python && uvicorn main:app --host 0.0.0.0 --port 8000`
- Region: Same as DB
- Plan: Free or Starter

**Environment Variables:**
```
SECRET_KEY=your_python_secret_key
DATABASE_URL=postgresql://user:password@database-host:5432/packaging_db
```

### 3. Go Backend
- Service Type: Web Service
- Build Command: `cd storage-backend/golang && go build -o main .`
- Start Command: `cd storage-backend/golang && ./main`
- Region: Same as DB
- Plan: Free or Starter

**Environment Variables:**
```
DATABASE_URL=postgresql://user:password@database-host:5432/packaging_db
JWT_SECRET_KEY=your_jwt_secret_key
PYTHON_BACKEND_URL=https://python-backend-url.onrender.com/calculate/python
```

### 4. React Frontend
- Service Type: Static Site
- Build Command: `cd storage-manager && npm ci && npm run build`
- Publish Directory: `storage-manager/build`
- Region: Any
- Plan: Free

**Build Settings:**
- Auto-deploy: ON
- Branch: main

## Deployment Steps

1. **Push repository ke GitHub**
```bash
git push origin main
```

2. **Login ke Render dashboard**
- Go to https://render.com
- Connect GitHub account

3. **Create PostgreSQL Service**
- Click "New +"
- Select "PostgreSQL"
- Configure settings
- Note the database URL

4. **Create Python Backend Service**
- Click "New Web Service"
- Connect GitHub repository
- Configure build and start commands
- Add environment variables
- Deploy

5. **Create Go Backend Service**
- Repeat step 4 for Go backend
- Set Python backend URL as environment variable

6. **Create Frontend Service**
- Click "New Static Site"
- Connect GitHub repository
- Configure build settings
- Set environment variable for API URL
- Deploy

## Expected URLs

- Frontend: `https://packaging-box-frontend.onrender.com`
- Go API: `https://packaging-box-go.onrender.com`
- Python API: `https://packaging-box-python.onrender.com`

## Monitoring

- Render Dashboard: View logs, restart services
- Health checks: Auto-enabled
- Auto-redeploy: On every git push to main

## Costs

- PostgreSQL: $7/month (minimum)
- Web Services: Free tier available (limited resources)