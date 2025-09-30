
# Stage 1: Build the Go application
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Copy go.mod and go.sum files and download dependencies
COPY go.mod ./
RUN go mod download

# Copy the rest of the source code
COPY . .

# Build the application
# -ldflags "-w -s" is used to make the binary smaller
RUN CGO_ENABLED=0 GOOS=linux go build -a -ldflags "-w -s" -o /app/main .

# Stage 2: Create the final, small image
FROM alpine:latest

WORKDIR /app

# Copy the built binary from the builder stage
COPY --from=builder /app/main .

# Expose the port the app runs on
EXPOSE 8080

# Set the command to run the application
CMD ["/app/main"]
