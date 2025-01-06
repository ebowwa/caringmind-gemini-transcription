#!/bin/bash

# Exit on error
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python installation
if ! command_exists python3; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Load environment variables
if [ -f ../.env ]; then
    set -a
    source ../.env
    set +a
else
    echo "Warning: ../.env file not found. Using default environment settings."
fi

# Check if Python virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate || {
    echo "Error: Failed to activate virtual environment"
    exit 1
}

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# Verify uvicorn installation
if ! command_exists uvicorn; then
    echo "Error: uvicorn not found after installation"
    exit 1
fi

# Start FastAPI server
echo "Starting FastAPI server..."
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
uvicorn main:app --reload --port ${PORT:-8000} --host ${HOST:-0.0.0.0}
