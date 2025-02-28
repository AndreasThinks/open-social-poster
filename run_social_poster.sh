#!/bin/bash

# Check if UV is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "UV not found. Installing UV..."
    # Install UV
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if [ $? -eq 0 ]; then
        echo "UV installed successfully"
    else
        echo "UV installation failed"
        exit 1
    fi
else
    echo "UV already installed"
fi

# Run the Python script using UV
echo "Running social_poster.py..."
uv run social_poster.py