#!/bin/bash
set -euo pipefail

# ---- Config ----
PROJECT_DIR="/Users/peterdankert/Documents/Entrepreneurship/Open Job Prospector"
STATE_FILE="$PROJECT_DIR/data/state.json"
LOG_DIR="$PROJECT_DIR/data/logs"
LOCK_FILE="$PROJECT_DIR/data/.pipeline.lock"
MAX_BUDGET="5.00"

# ---- Ensure directories exist ----
mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$STATE_FILE")"

# ---- Lock file to prevent overlapping runs ----
if [ -f "$LOCK_FILE" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK_FILE") ))
    if [ "$LOCK_AGE" -gt 7200 ]; then
        echo "WARNING: Stale lock file (${LOCK_AGE}s old). Removing."
        rm -f "$LOCK_FILE"
    else
        echo "Pipeline already running (lock age: ${LOCK_AGE}s). Exiting."
        exit 0
    fi
fi
trap 'rm -f "$LOCK_FILE"' EXIT
touch "$LOCK_FILE"

# ---- Initialize state file if missing ----
if [ ! -f "$STATE_FILE" ]; then
    cat > "$STATE_FILE" << 'INIT'
{
  "version": 1,
  "last_run": null,
  "last_run_status": null,
  "search_config": {
    "role_keywords": ["medical records clerk", "EHR analyst", "health information technician"],
    "location": "",
    "num_results": 10
  },
  "jobs": {}
}
INIT
fi

# ---- Source API keys ----
source "$PROJECT_DIR/.gitignore/.env"

# ---- Build the prompt ----
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PROMPT="Run /job-prospector in incremental mode.

State file: data/state.json
Timestamp: $TIMESTAMP

Read the state file first. Use search_config for parameters (do not ask me).
After Stage 1, deduplicate against existing jobs in state.
Only process NEW jobs through Stages 2-4.
Update the state file when done.
Do not ask any questions -- run autonomously and exit."

# ---- Run Claude CLI ----
RUN_LOG="$LOG_DIR/run-$(date +%Y%m%d-%H%M%S).log"

cd "$PROJECT_DIR"
claude -p \
  --dangerously-skip-permissions \
  --max-budget-usd "$MAX_BUDGET" \
  "$PROMPT" \
  2>&1 | tee "$RUN_LOG"

EXIT_CODE=${PIPESTATUS[0]}

# ---- Log result ----
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Pipeline completed successfully" >> "$LOG_DIR/history.log"
else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Pipeline failed with exit code $EXIT_CODE" >> "$LOG_DIR/history.log"
fi

exit $EXIT_CODE
