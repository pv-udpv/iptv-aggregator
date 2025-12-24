#!/usr/bin/env bash
#
# pullrun.sh - Universal script for git pull + command execution
#
# Usage:
#   ./pullrun.sh <command> [args...]
#
# Examples:
#   ./pullrun.sh python scripts/extract_tvg_country.py
#   ./pullrun.sh python scripts/download_epg.py
#   ./pullrun.sh python scripts/parse_epg_pydantic.py epg/cache/cnn.us.xml
#   ./pullrun.sh bash -c "python scripts/download_epg.py && python scripts/generate_m3u_with_epg.py"
#
# Features:
# - Always git pull first
# - Activate .venv automatically
# - Install missing deps if needed
# - Show execution time
# - Exit on any error

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}🚀 pullrun.sh - Git Pull + Command Runner${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""

# Start time
START_TIME=$(date +%s)

# Step 1: Git pull
echo -e "${YELLOW}[1/4] Git pull...${NC}"
if git pull origin main --quiet; then
    echo -e "${GREEN}✓ Up to date${NC}"
else
    echo -e "${RED}✗ Git pull failed${NC}"
    exit 1
fi
echo ""

# Step 2: Check .venv
echo -e "${YELLOW}[2/4] Checking virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ .venv not found. Creating...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ .venv created${NC}"
else
    echo -e "${GREEN}✓ .venv exists${NC}"
fi
echo ""

# Step 3: Activate .venv
echo -e "${YELLOW}[3/4] Activating virtual environment...${NC}"
source .venv/bin/activate
echo -e "${GREEN}✓ Activated${NC}"
echo ""

# Step 4: Check dependencies (optional)
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}[3.5/4] Checking dependencies...${NC}"
    
    # Quick check if key packages exist
    if python -c "import pydantic, httpx, rapidfuzz, pydantic_xml" 2>/dev/null; then
        echo -e "${GREEN}✓ All deps installed${NC}"
    else
        echo -e "${YELLOW}⚠ Installing missing dependencies...${NC}"
        if command -v uv &> /dev/null; then
            uv pip install -r requirements.txt --quiet
        else
            pip install -r requirements.txt --quiet
        fi
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    fi
    echo ""
fi

# Step 5: Run command
echo -e "${YELLOW}[4/4] Running command...${NC}"
echo -e "${BLUE}Command: $*${NC}"
echo ""
echo -e "${BLUE}======================================================================${NC}"
echo ""

# Execute
if "$@"; then
    echo ""
    echo -e "${BLUE}======================================================================${NC}"
    
    # Calculate duration
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo -e "${GREEN}✓ Success${NC}"
    echo -e "${GREEN}⏱  Duration: ${DURATION}s${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    exit 0
else
    echo ""
    echo -e "${BLUE}======================================================================${NC}"
    echo -e "${RED}✗ Command failed${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    exit 1
fi
