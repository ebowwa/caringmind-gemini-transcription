#!/bin/bash

# Exit on error
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if lsof is installed (needed to find process by port)
if ! command_exists lsof; then
    echo "Error: lsof is not installed. Please install it first."
    exit 1
fi

# Default port value if not specified in .env
DEFAULT_PORT=8000

# Load environment variables if .env exists
if [ -f "$SCRIPT_DIR/../.env" ]; then
    set -a
    source "$SCRIPT_DIR/../.env"
    set +a
fi

# Use PORT from env or default
PORT=${PORT:-$DEFAULT_PORT}

# Find PID of process running on the specified port
PID=$(lsof -ti tcp:${PORT})

if [ -z "$PID" ]; then
    echo "No process found running on port ${PORT}"
    exit 0
fi

echo "Found server process running with PID: ${PID}"

# Try graceful shutdown first
echo "Attempting graceful shutdown..."
kill -15 $PID 2>/dev/null || true

# Wait for up to 5 seconds for graceful shutdown
COUNTER=0
while [ $COUNTER -lt 5 ]; do
    if ! kill -0 $PID 2>/dev/null; then
        echo "Server stopped successfully"
        exit 0
    fi
    sleep 1
    COUNTER=$((COUNTER + 1))
done

# If process still running, force kill
if kill -0 $PID 2>/dev/null; then
    echo "Graceful shutdown failed. Force killing the process..."
    kill -9 $PID
    echo "Server forcefully stopped"
fi

# Cleanup any leftover .pid files if they exist
if [ -f "$SCRIPT_DIR/server.pid" ]; then
    rm "$SCRIPT_DIR/server.pid"
fi

echo "Server shutdown complete"