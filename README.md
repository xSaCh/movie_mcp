# MCP Server

A lightweight Model Context Protocol (MCP) server for managing movie/TV series watchlists using TMDB data. Built with FastAPI, raw SQL, and Pydantic.

## Features

- Search, discover, and fetch movie/TV metadata via TMDB API  
- Track watchlist items with statuses: `PlanToWatch`, `Watching`, `Watched`, `Dropped`, `OnHold`  
- Store film info, metadata, and genres in SQLite using raw SQL  
- JSON-RPC-style MCP interface over HTTP for structured command handling  

## Tech Stack

- Python, FastAPI, Pydantic  
- SQLite
- TMDB API

## Sample 
![image](https://github.com/user-attachments/assets/1a1e204f-a536-4b09-9a13-442cd7341e2b)

## Run Locally
#### API Server

```bash
git clone https://github.com/yourusername/mcp-server.git
cd mcp-server
pip install -r requirements.txt

export TMDB_API_KEY=your_tmdb_key_here
uvicorn main:app --reload
```
NOTE: Create '.env' and add TMDB_API_KEY variable there

#### MCP Config file (Claude Config compatible)
- UV (Recommended)
  Note: Install and configure (uv)[https://docs.astral.sh/uv/guides/tools/] for mcp before excuting
```json
{
  "mcpServers": {
    "Movie MCP": {
      "command": "uv",
      "args": [
        "run",
        "mcp", "run", "[path_to_mcp_tmdb]/mcp_server.py"
      ]
    }
  }
}
````
- Hacky way 
```json
{
  "mcpServers": {
    
    "Movie MCP": {
      "command": "[path_to_mcp_tmdb]/setup.sh",
      "args": []
    }
  }
}
```
Use any Claude mcp config client and add above config. 
Use [Console-chat-gpt](https://github.com/amidabuddha/console-chat-gpt) CLI based chat MCP Client

Alternatively use (mcptools)[https://github.com/f/mcptools/]
- List tools 
```bash
cd [path_to_movie_mcp]
mcptools tools uv run mcp run mcp_server.py
```
- Search Movie 
```bash
cd [path_to_movie_mcp]
mcptools call search_tmdb --params '{"query":"final destination", "type":"movie"}' uv run mcp run mcp_server.py
```
