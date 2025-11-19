# Network MCP Backend

This directory contains a small FastAPI backend that wraps an LLM client and an MCP (Multi-Component Process) session to provide a networked agent capable of calling tools exposed by an MCP server. It's intended as an example/custom agent implementation that enables the LLM to interact with external tools (search, browser automation, etc.) via MCP.

## Features
- Loads API credentials from environment variables or a local `.env` file.
- Starts an MCP client session (via `mcp.client.stdio`) and exposes a `/chat` endpoint that relays messages to the model and executes tool calls returned by the model.
- CORS-enabled for quick local testing.

## Quick start

1. Copy or edit the `.env` file in this directory to include your API key and optional settings (already included as a template):

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

2. Install dependencies (make sure `python-dotenv` is installed):

```bash
uv pip install -r ../requirements.txt
uv pip install python-dotenv
```

3. Run the backend (development):

```bash
# from the network-mcp directory
python backend.py
```

Or run via uvicorn for production-like behavior:

```bash
uvicorn backend:app --host 0.0.0.0 --port 8000
```

## API: /chat

POST /chat

Request body (JSON):

```json
{
	"message": "your question here",
	"history": []
}
```

Response:
- If the model answers directly, you get: `{ "response": "..." }`.
- If the model requests tool calls, the backend will invoke the tool(s) via MCP and continue the conversation until a final reply or timeout.

## Configuration
- Environment variables supported:
	- `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, or `API_KEY` (first one found is used)
	- `BASE_URL` (defaults to `https://api.deepseek.com`)
	- `MODEL_NAME` (defaults to `deepseek-chat`)

Place these in `network-mcp/.env` for local development. Do NOT commit production keys to git.

## Security & Deployment notes
- Keep your API keys private. Add `network-mcp/.env` to `.gitignore` or manage secrets in your deployment platform.
- In production, prefer setting environment variables via your CI/CD or hosting provider instead of `.env` files.

## Troubleshooting
- If you see `API key not set` on startup, ensure the `.env` file is present and contains a real key or export the env var before running.
- If MCP connection fails, check that the MCP server (`mcp_tool.py` or the configured command) is available and working.

## Extending
- Add more robust validation for `BASE_URL` and `MODEL_NAME` if you use multiple model endpoints.
- Add authentication for the `/chat` endpoint if exposing it beyond local dev.

---
Short and focused README for the custom networked agent. If you want, I can also add an example curl request or a small client script that calls `/chat`.

