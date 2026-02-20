# Vertex AI Setup with Service Account

## ✅ Configuration Complete

Your LangGraph supervisor is now configured to use Google Cloud Vertex AI with service account authentication.

### Service Account Details
- **Project ID**: `gcp-jai-platform-dev`
- **Service Account**: `admin-panel-agentos@gcp-jai-platform-dev.iam.gserviceaccount.com`
- **Credentials File**: `gcp-service-account.json` (mounted in container)

### Environment Variables Set
```bash
GOOGLE_CLOUD_PROJECT=gcp-jai-platform-dev
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-service-account.json
```

## Available Vertex AI Models

When creating agents in Agent Studio, you can now use these Vertex AI models **without needing GOOGLE_API_KEY**:

### Recommended Models (via Vertex AI)
- **`google_vertexai:gemini-2.0-flash-exp`** — Latest Gemini 2.0 Flash (experimental)
- **`google_vertexai:gemini-1.5-pro`** — Gemini 1.5 Pro (production-ready)
- **`google_vertexai:gemini-1.5-flash`** — Gemini 1.5 Flash (fast & cost-effective)
- **`google_vertexai:gemini-1.5-flash-8b`** — Gemini 1.5 Flash 8B (smallest, fastest)

### How to Use

1. **Create a new agent** in Agent Studio
2. In the **Model** dropdown, select a Vertex AI model (e.g., `gemini-1.5-flash`)
3. The agent will automatically use your service account for authentication

### Model ID Mapping

The backend automatically maps between Agent Studio's short model names and LangGraph's provider-prefixed format:

| Agent Studio UI | LangGraph Format |
|----------------|------------------|
| `gemini-2.0-flash` | `google_vertexai:gemini-2.0-flash-exp` |
| `gemini-1.5-pro` | `google_vertexai:gemini-1.5-pro` |
| `gemini-1.5-flash` | `google_vertexai:gemini-1.5-flash` |

This mapping is handled in `backend/langgraph_client/client.py`.

### Other Available Models (via API Keys)

You also have these models configured via API keys:
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo` (requires `OPENAI_API_KEY` ✅)
- **Anthropic**: `claude-sonnet-4`, `claude-opus-4`, `claude-haiku-4` (requires `ANTHROPIC_API_KEY` ✅)

## Troubleshooting

### Check if service account is working
```bash
docker exec oap-supervisor python -c "import os; print('Project:', os.getenv('GOOGLE_CLOUD_PROJECT')); print('Creds:', os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))"
```

### View LangGraph logs
```bash
docker logs oap-supervisor --tail 50
```

### Restart LangGraph supervisor
```bash
docker compose restart langgraph-supervisor
```

## Security Note

The `gcp-service-account.json` file has been added to `.gitignore` to prevent accidental commits to version control.
