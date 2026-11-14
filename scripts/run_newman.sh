#!/usr/bin/env bash
set -e

# Change directory to the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Create reports directory if missing
mkdir -p reports

# Locate newman executable
if [ -f "./node_modules/newman/bin/newman.js" ]; then
    NEWMAN_CMD="node ./node_modules/newman/bin/newman.js"
elif command -v newman >/dev/null 2>&1; then
    NEWMAN_CMD="newman"
else
    NEWMAN_CMD="npx --yes newman"
fi

echo "=========================================================="
echo "Starting Newman Test Runner..."
echo "Collection: postman/hr_attendance_collection.json"
echo "Environment: postman/local_env.json"
echo "Reporters: cli, htmlextra -> reports/newman_report.html"
echo "=========================================================="

# Check if target server is live
SERVER_URL="http://127.0.0.1:8000/api/v1/test/reset"
SERVER_STARTED_BY_SCRIPT=0

if ! curl -s -f -X POST "${SERVER_URL}" >/dev/null 2>&1; then
    echo "FastAPI server is not currently running. Starting it in background..."
    if [ -f "./venv/Scripts/python.exe" ]; then
        PY_BIN="./venv/Scripts/python.exe"
    elif [ -f "./venv/bin/python" ]; then
        PY_BIN="./venv/bin/python"
    else
        PY_BIN="python"
    fi

    PYTHONPATH="." $PY_BIN -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >/dev/null 2>&1 &
    SERVER_PID=$!
    SERVER_STARTED_BY_SCRIPT=1

    # Wait for server to become responsive
    MAX_RETRIES=20
    COUNT=0
    until curl -s -f -X POST "${SERVER_URL}" >/dev/null 2>&1; do
        sleep 0.5
        COUNT=$((COUNT + 1))
        if [ $COUNT -ge $MAX_RETRIES ]; then
            echo "ERROR: FastAPI server failed to start within 10 seconds."
            kill $SERVER_PID 2>/dev/null || true
            exit 1
        fi
    done
    echo "FastAPI server started successfully on PID ${SERVER_PID}."
fi

# Execute Newman
echo "Executing Newman collection..."
$NEWMAN_CMD run postman/hr_attendance_collection.json \
    -e postman/local_env.json \
    --reporters cli,htmlextra \
    --reporter-htmlextra-export reports/newman_report.html

NEWMAN_EXIT_CODE=$?

# Teardown background server if this script started it
if [ $SERVER_STARTED_BY_SCRIPT -eq 1 ]; then
    echo "Stopping background FastAPI server (PID ${SERVER_PID})..."
    kill $SERVER_PID 2>/dev/null || true
fi

if [ $NEWMAN_EXIT_CODE -eq 0 ]; then
    echo "=========================================================="
    echo "SUCCESS: Newman suite passed with 0 failures!"
    echo "HTML Report available at: reports/newman_report.html"
    echo "=========================================================="
else
    echo "=========================================================="
    echo "FAILURE: Newman suite reported failures (exit code ${NEWMAN_EXIT_CODE})."
    echo "=========================================================="
fi

exit $NEWMAN_EXIT_CODE
