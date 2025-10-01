# 🔐 SECURITY SETUP GUIDE

**⚠️ IMPORTANT: This project requires manual security configuration before it can run.**

## 🚨 Why This Setup is Required

This repository is public, so we've removed all sensitive information like:
- Database passwords
- JWT secret keys  
- API credentials
- Configuration files with secrets

**The application WILL NOT start without proper configuration.**

---

## 🔧 Quick Setup (5 minutes)

### 1. Copy Template Files

```bash
# Copy environment template
cp .env.example .env

# Copy Docker Compose template  
cp docker-compose.yml.example docker-compose.yml
```

### 2. Configure Your Secrets

Edit `.env` file and replace ALL placeholder values:

```bash
# Open in your preferred editor
nano .env
# or
code .env
```

**Required Changes:**
```env
# Database - USE STRONG PASSWORDS
POSTGRES_DB=packaging_db
POSTGRES_USER=your_actual_username        # ← CHANGE THIS
POSTGRES_PASSWORD=your_very_secure_pass   # ← CHANGE THIS (min 12 chars)

# JWT Security - CRITICAL FOR AUTH
JWT_SECRET_KEY=your_super_secure_jwt_secret_minimum_32_characters_long  # ← CHANGE THIS

# Python Backend
PYTHON_SECRET_KEY=another_secure_key_for_python_backend  # ← CHANGE THIS
```

### 3. Generate Secure Keys

**For JWT_SECRET_KEY (Go backend):**
```bash
# Generate 64-character random key
openssl rand -hex 32
```

**For PYTHON_SECRET_KEY:**
```bash
# Generate another secure key
openssl rand -hex 32
```

### 4. Start the Application

```bash
# Build and start all services
docker compose up --build

# Application will be available at:
# - Frontend: http://localhost:3000
# - Go API: http://localhost:8080
# - Python API: http://localhost:8000
```

---

## 🛡️ Security Best Practices

### Password Requirements
- **Database Password**: Minimum 12 characters, mix of letters/numbers/symbols
- **JWT Secret**: Minimum 32 characters, use generated random strings
- **Python Secret**: Minimum 32 characters, different from JWT secret

### Examples of GOOD secrets:
```env
# Good - randomly generated
JWT_SECRET_KEY=f4a2b8c9d1e3f7g8h9i2j4k5l7m8n9o1p3q5r7s9t2u4v6w8x1y3z5a7b9c2d4e6
POSTGRES_PASSWORD=MySecure#Database$Password123!
```

### Examples of BAD secrets (DON'T USE):
```env
# Bad - too simple/common
JWT_SECRET_KEY=mysecret
POSTGRES_PASSWORD=password123
JWT_SECRET_KEY=your-super-secure-jwt-secret  # template value
```

---

## 🔍 Troubleshooting

### Application Won't Start

**Error: "DATABASE_URL environment variable is required"**
- Solution: Make sure you copied `.env.example` to `.env` and filled in all values

**Error: "JWT_SECRET_KEY environment variable is required"**  
- Solution: Set a proper JWT secret key (minimum 32 characters)

**Error: "SECRET_KEY environment variable is required"**
- Solution: Set PYTHON_SECRET_KEY in your `.env` file

### Database Connection Issues

**Error: "Failed to connect to database"**
- Check your POSTGRES_USER and POSTGRES_PASSWORD in `.env`
- Make sure Docker containers are running: `docker compose ps`

### Port Conflicts

**Error: "Port already in use"**
- Change ports in `docker-compose.yml` if 3000, 8000, 8080, or 5432 are occupied
- Or stop conflicting services

---

## 📁 File Structure After Setup

```
packaging-box-dashboard/
├── .env                    # ← Your secrets (NEVER commit)
├── .env.example           # ← Template (safe to commit)
├── docker-compose.yml     # ← Your config (NEVER commit) 
├── docker-compose.yml.example  # ← Template (safe to commit)
├── .gitignore            # ← Protects your secrets
└── SETUP.md              # ← This file
```

---

## 🚫 What NOT to Do

- ❌ **Never commit `.env` or `docker-compose.yml`** - they contain your secrets
- ❌ **Never share your actual secret keys** in issues, pull requests, or messages  
- ❌ **Never use the example/template values** in production
- ❌ **Never reuse the same secret** for multiple purposes

---

## ✅ Production Deployment

For production environments:

1. **Use proper secret management** (AWS Secrets Manager, Azure Key Vault, etc.)
2. **Use environment-specific `.env` files** (`.env.production`, `.env.staging`)
3. **Enable HTTPS/TLS** with proper certificates
4. **Use managed databases** instead of Docker containers
5. **Implement proper backup strategies**

---

## 🆘 Need Help?

1. **Check the logs**: `docker compose logs`
2. **Verify your config**: `docker compose config`
3. **Restart services**: `docker compose restart`
4. **Reset everything**: `docker compose down -v && docker compose up --build`

If you're still having issues, create an issue in the repository but **DO NOT include your actual secret keys** in the issue description.

---

## 🔒 Security Checklist

Before running in production, verify:

- [ ] All template values replaced with real secrets
- [ ] JWT_SECRET_KEY is at least 32 characters
- [ ] Database password is strong (12+ characters)  
- [ ] `.env` file is in `.gitignore` and not committed
- [ ] `docker-compose.yml` is in `.gitignore` and not committed
- [ ] Different secrets used for different services
- [ ] Secrets generated randomly (not manually typed)

**✨ Once configured properly, the application will start successfully and be ready for development or testing!**