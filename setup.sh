#!/usr/bin/zsh

SCRIPT_DIR="${0:A:h}" 
source "$SCRIPT_DIR/venv/bin/activate"
mcp run "$SCRIPT_DIR/mcp_server.py"