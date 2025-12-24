#!/usr/bin/env bash
# pullrun.sh - Universal command runner with error handling & git snapshots
# Usage: ./pullrun.sh [--no-commit] <command>

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

ERROR_DIR=".pullrun/errors"
LOG_DIR=".pullrun/logs"
ERROR_BRANCH="debug/pullrun-errors"
MAX_ERROR_LOGS=10
COMMIT_ERRORS=true

# Parse flags
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-commit)
            COMMIT_ERRORS=false
            shift
            ;;
        *)
            break
            ;;
    esac
done

if [ $# -eq 0 ]; then
    echo "Usage: ./pullrun.sh [--no-commit] <command>"
    echo "Example: ./pullrun.sh python scripts/download_epg.py"
    exit 1
fi

# ============================================================================
# COLORS & HELPERS
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }

# ============================================================================
# ERROR HANDLING SETUP
# ============================================================================

mkdir -p "$ERROR_DIR" "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ERROR_LOG="$ERROR_DIR/error_${TIMESTAMP}.log"
RUN_LOG="$LOG_DIR/run_${TIMESTAMP}.log"

cleanup_old_logs() {
    # Keep only last N error logs
    local count=$(ls -1 "$ERROR_DIR" 2>/dev/null | wc -l)
    if [ "$count" -gt "$MAX_ERROR_LOGS" ]; then
        log_info "Cleaning old error logs (keeping last $MAX_ERROR_LOGS)..."
        ls -1t "$ERROR_DIR" | tail -n +$((MAX_ERROR_LOGS + 1)) | xargs -I {} rm -f "$ERROR_DIR/{}"
    fi
}

create_error_snapshot() {
    local exit_code=$1
    local command="$2"
    local error_output="$3"
    
    log_error "Command failed with exit code $exit_code"
    
    # Create error report
    cat > "$ERROR_LOG" <<EOF
========================================
PULLRUN ERROR REPORT
========================================
Timestamp: $(date -Iseconds)
Exit Code: $exit_code
Command: $command
Working Dir: $(pwd)
User: $(whoami)
Git Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "N/A")
Git Commit: $(git rev-parse --short HEAD 2>/dev/null || echo "N/A")

========================================
ERROR OUTPUT
========================================
$error_output

========================================
ENVIRONMENT
========================================
Python: $(python --version 2>&1 || echo "N/A")
Pip: $(pip --version 2>&1 || echo "N/A")
Venv Active: ${VIRTUAL_ENV:-"No"}

========================================
LAST 20 LINES OF STDOUT/STDERR
========================================
$(tail -20 "$RUN_LOG" 2>/dev/null || echo "No log available")

========================================
RECENT GIT COMMITS
========================================
$(git log --oneline -5 2>/dev/null || echo "N/A")

========================================
FILE TREE (relevant)
========================================
$(tree -L 2 -I '.venv|__pycache__|*.pyc' 2>/dev/null || ls -lah)
EOF
    
    log_info "Error report saved: $ERROR_LOG"
    
    # Git commit error snapshot if enabled
    if [ "$COMMIT_ERRORS" = true ]; then
        commit_error_snapshot "$exit_code" "$command"
    fi
    
    cleanup_old_logs
}

commit_error_snapshot() {
    local exit_code=$1
    local command="$2"
    
    log_info "Creating error snapshot commit..."
    
    # Ensure error branch exists
    if ! git show-ref --verify --quiet "refs/heads/$ERROR_BRANCH"; then
        log_info "Creating debug branch: $ERROR_BRANCH"
        git branch "$ERROR_BRANCH" 2>/dev/null || true
    fi
    
    # Store current branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    
    # Switch to error branch
    if git checkout "$ERROR_BRANCH" 2>/dev/null; then
        # Add error logs
        git add "$ERROR_DIR" "$LOG_DIR" 2>/dev/null || true
        
        # Create commit with error context
        local commit_msg="error: command failed with exit code $exit_code

Command: $command
Timestamp: $TIMESTAMP
Branch: $current_branch

See: $ERROR_LOG"
        
        if git commit -m "$commit_msg" --no-verify 2>/dev/null; then
            local commit_hash=$(git rev-parse --short HEAD)
            log_success "Error snapshot committed: $commit_hash"
            log_info "View: git show $commit_hash"
            log_info "Checkout branch: git checkout $ERROR_BRANCH"
        else
            log_warn "No changes to commit (error logs already tracked)"
        fi
        
        # Switch back to original branch
        git checkout "$current_branch" 2>/dev/null || true
    else
        log_warn "Failed to switch to error branch, skipping commit"
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

START_TIME=$(date +%s)

echo ""
echo "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo "${BLUE}║${NC}  🚀 PULLRUN - Universal Command Runner with Error Handling ${BLUE}║${NC}"
echo "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Git pull
log_info "[1/4] Git pull..."
if git pull origin main &>> "$RUN_LOG"; then
    log_success "Code updated"
else
    log_warn "Git pull failed (continuing...)"
fi

# Step 2: Check/create .venv
log_info "[2/4] Checking .venv..."
if [ ! -d ".venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv .venv &>> "$RUN_LOG"
    log_success "Virtual environment created"
else
    log_success "Virtual environment exists"
fi

# Step 3: Activate .venv
log_info "[3/4] Activating .venv..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    log_success "Virtual environment activated"
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
    log_success "Virtual environment activated (Windows)"
else
    log_error "Failed to find activate script"
    exit 1
fi

# Step 3.5: Check dependencies
log_info "[3.5/4] Checking dependencies..."
if [ -f "requirements.txt" ]; then
    if pip install -q -r requirements.txt &>> "$RUN_LOG"; then
        log_success "Dependencies installed"
    else
        log_warn "Some dependencies failed (continuing...)"
    fi
else
    log_warn "No requirements.txt found"
fi

# Step 4: Run command with error capture
log_info "[4/4] Running command: $*"
echo ""

# Execute command and capture output
if "$@" 2>&1 | tee -a "$RUN_LOG"; then
    EXIT_CODE=0
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo "${GREEN}║${NC}  ✓ SUCCESS                                                   ${GREEN}║${NC}"
    echo "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
    echo "${GREEN}║${NC}  ⏱  Duration: ${DURATION}s                                             ${GREEN}║${NC}"
    echo "${GREEN}║${NC}  📁 Logs: $RUN_LOG                                          ${GREEN}║${NC}"
    echo "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
else
    EXIT_CODE=$?
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # Capture error output
    ERROR_OUTPUT=$(tail -50 "$RUN_LOG" 2>/dev/null || echo "No output captured")
    
    echo ""
    echo "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo "${RED}║${NC}  ✗ FAILURE                                                   ${RED}║${NC}"
    echo "${RED}╠════════════════════════════════════════════════════════════════╣${NC}"
    echo "${RED}║${NC}  Exit Code: $EXIT_CODE                                             ${RED}║${NC}"
    echo "${RED}║${NC}  Duration: ${DURATION}s                                              ${RED}║${NC}"
    echo "${RED}║${NC}  Command: $*                                                 ${RED}║${NC}"
    echo "${RED}╠════════════════════════════════════════════════════════════════╣${NC}"
    echo "${RED}║${NC}  📋 Error Report: $ERROR_LOG                                ${RED}║${NC}"
    echo "${RED}║${NC}  📋 Run Log: $RUN_LOG                                       ${RED}║${NC}"
    if [ "$COMMIT_ERRORS" = true ]; then
        echo "${RED}║${NC}  🔍 Debug Branch: $ERROR_BRANCH                             ${RED}║${NC}"
    fi
    echo "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Create error snapshot
    create_error_snapshot "$EXIT_CODE" "$*" "$ERROR_OUTPUT"
    
    log_error "See error report for details: $ERROR_LOG"
    
    if [ "$COMMIT_ERRORS" = true ]; then
        echo ""
        log_info "To view error snapshot:"
        echo "  git checkout $ERROR_BRANCH"
        echo "  git log --oneline -1"
        echo "  cat $ERROR_LOG"
    fi
    
    exit "$EXIT_CODE"
fi
