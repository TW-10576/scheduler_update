#!/bin/bash

###############################################################################
# Shift Scheduler - Development Startup Script
#
# This script starts PostgreSQL in Docker only.
# Backend and Frontend must be started separately.
#
# Usage: bash start-dev.sh
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Shift Scheduler - Development Environment${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running. Please start Docker.${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Starting PostgreSQL database...${NC}\n"

# Navigate to project root
cd "$SCRIPT_DIR"

# Start PostgreSQL
docker compose up -d

# Wait for PostgreSQL to be ready
echo -e "\n${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker compose exec -T postgres pg_isready -U postgres &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready!${NC}\n"
        break
    fi
    echo "   Attempt $attempt/$max_attempts..."
    sleep 1
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo -e "${RED}❌ PostgreSQL failed to start after $max_attempts attempts${NC}"
    exit 1
fi

# Display startup information
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ PostgreSQL Database Started Successfully!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Database Details:${NC}"
echo -e "   Host: ${GREEN}localhost${NC}"
echo -e "   Port: ${GREEN}5432${NC}"
echo -e "   User: ${GREEN}postgres${NC}"
echo -e "   Password: ${GREEN}postgres123${NC}"
echo -e "   Database: ${GREEN}shift_scheduler${NC}\n"

echo -e "${YELLOW}Next Steps - Start Backend & Frontend:${NC}"
echo -e "\n${BLUE}Terminal 2 - Backend:${NC}"
echo -e "   cd ${SCRIPT_DIR}/backend"
echo -e "   python run.py\n"

echo -e "${BLUE}Terminal 3 - Frontend:${NC}"
echo -e "   cd ${SCRIPT_DIR}/frontend"
echo -e "   npm run dev\n"

echo -e "${YELLOW}Access:${NC}"
echo -e "   Frontend: ${GREEN}http://localhost:5173${NC}"
echo -e "   Backend: ${GREEN}http://localhost:8000${NC}"
echo -e "   API Docs: ${GREEN}http://localhost:8000/docs${NC}\n"

echo -e "${YELLOW}Useful Commands:${NC}"
echo -e "   Stop Database: ${GREEN}docker compose down${NC}"
echo -e "   View Logs: ${GREEN}docker compose logs -f postgres${NC}"
echo -e "   Remove Data: ${GREEN}docker compose down -v${NC}\n"

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Ready for development!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"

# Keep the script running to show logs
echo -e "${YELLOW}PostgreSQL logs (press Ctrl+C to exit):${NC}\n"
docker compose logs -f postgres
