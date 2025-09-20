#!/bin/bash
# Wrapper script to run the Spotify MCP server with proper environment

# Change to the project directory
cd "/Users/vidit/Desktop/dev/mcp_spotify"

# Activate the virtual environment
source venv/bin/activate

# Set environment variables if .env file exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the MCP server
exec python mcp_server.py "$@"
