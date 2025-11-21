#!/bin/bash

# Simple run script for local development

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the application using python -m to ensure correct Python interpreter
# --timeout-keep-alive: Keep connections alive for 10 minutes
# --limit-concurrency: Allow multiple concurrent requests
# Note: For large file uploads, uvicorn will handle them, but you may need to increase
# system limits (ulimit -n for file descriptors) for very large files
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --timeout-keep-alive 600

