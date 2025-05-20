from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("Joke Server")


@mcp.tool()
def get_jokes() -> dict:
    """Fetch 10 random jokes from an external API."""
    try:
        response = requests.get("https://official-joke-api.appspot.com/jokes/ten")
        response.raise_for_status()
        jokes = response.json()
        formatted = [f"{j['setup']} {j['punchline']}" for j in jokes]
        return {"jokes": formatted}
    except Exception as e:
        return {"error": str(e)}
