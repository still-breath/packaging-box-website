# AWS Deployment Configuration
# Deploy menggunakan AWS ECS + RDS + ECR

## Arsitektur AWS

```
GitHub (Source)
    ↓
GitHub Actions (Build)
    ↓
Amazon ECR (Container Registry)
    ↓
ECS Cluster (Container Orchestration)
    ├── Go Backend (Fargate)
    ├── Python Backend (Fargate)
    └── React Frontend (CloudFront + S3)
    ↓
RDS PostgreSQL (Managed Database)
```

## Prerequisites

- AWS Account dengan credentials
- AWS CLI configured locally
- IAM role dengan permissions untuk ECR, ECS, RDS, CloudFormation

## Step 1: Setup RDS PostgreSQL

```bash
# Menggunakan AWS Console atau CLI
aws rds create-db-instance \
  --db-instance-identifier packaging-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password YourSecurePassword123! \
  --allocated-storage 20 \
  --backup-retention-period 7 \
  --enable-cloudwatch-logs-exports postgresql
```

## Step 2: Setup Amazon ECR

```bash
# Create ECR repositories
aws ecr create-repository --repository-name packaging-box/go-backend --region us-east-1
aws ecr create-repository --repository-name packaging-box/python-backend --region us-east-1
aws ecr create-repository --repository-name packaging-box/frontend --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
```

## Step 3: Build and Push Docker Images

```bash
# Go Backend
docker build -t 123456789.dkr.ecr.us-east-1.amazonaws.com/packaging-box/go-backend:latest ./storage-backend/golang
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/packaging-box/go-backend:latest

# Python Backend
docker build -t 123456789.dkr.ecr.us-east-1.amazonaws.com/packaging-box/python-backend:latest ./storage-backend/python
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/packaging-box/python-backend:latest

# Frontend
docker build -t 123456789.dkr.ecr.us-east-1.amazonaws.com/packaging-box/frontend:latest ./storage-manager
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/packaging-box/frontend:latest
```

## Step 4: Setup ECS Cluster

```bash
# Create ECS Cluster
aws ecs create-cluster --cluster-name packaging-box-cluster --region us-east-1

# Create CloudWatch Log Group
aws logs create-log-group --log-group-name /ecs/packaging-box --region us-east-1
```

## Step 5: Create ECS Task Definitions

### Go Backend Task Definition

```json
{
  "family": "go-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "go-backend",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/packaging-box/go-backend:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgres://admin:password@packaging-db.xxx.us-east-1.rds.amazonaws.com:5432/packaging_db"
        },
        {
          "name": "JWT_SECRET_KEY",
          "value": "your-secret-key-here"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/packaging-box",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "go-backend"
        }
      }
    }
  ]
}
```

## Step 6: Create ECS Services

```bash
# Go Backend Service
aws ecs create-service \
  --cluster packaging-box-cluster \
  --service-name go-backend \
  --task-definition go-backend:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=go-backend,containerPort=8080
```

## Step 7: Setup Application Load Balancer (ALB)

```bash
# Create Target Groups
aws elbv2 create-target-group --name go-backend-tg --protocol HTTP --port 8080 --vpc-id vpc-xxx

# Create Application Load Balancer
aws elbv2 create-load-balancer --name packaging-box-alb --subnets subnet-xxx subnet-xxx

# Register targets
aws elbv2 register-targets --target-group-arn arn:aws:elasticloadbalancing:... --targets Id=xxx,Port=8080
```

## Step 8: GitHub Actions Integration

Add these secrets ke GitHub:

```
AWS_ACCOUNT_ID: 123456789
AWS_REGION: us-east-1
AWS_ACCESS_KEY_ID: your_access_key
AWS_SECRET_ACCESS_KEY: your_secret_key
ECR_REPOSITORY_GO: packaging-box/go-backend
ECR_REPOSITORY_PYTHON: packaging-box/python-backend
ECR_REPOSITORY_FRONTEND: packaging-box/frontend
ECS_CLUSTER: packaging-box-cluster
```

## Step 9: Auto-deployment

GitHub Actions akan automatically:
1. Build Docker images
2. Push ke ECR
3. Update ECS task definitions
4. Deploy new versions

## Cost Estimation

- RDS (db.t3.micro): ~$30/month
- ECS Fargate (2 containers): ~$50/month
- ALB: ~$16/month
- Data transfer: ~$5-10/month
- **Total**: ~$100-120/month

## Monitoring & Logging

- CloudWatch Logs: `/ecs/packaging-box`
- CloudWatch Metrics: CPU, Memory, Network
- X-Ray: Optional distributed tracing
- SNS Alerts: Optional notifications

## Resources

- AWS Docs: https://docs.aws.amazon.com/ecs/
- ECS Best Practices: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/best_practices.html
- Cost Calculator: https://calculator.aws/