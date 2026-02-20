FROM python:3.11-slim

WORKDIR /app

# Install uv for faster dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY langgraph_supervisor/ ./langgraph_supervisor/
COPY langgraph.json ./

# Expose the default LangGraph port
EXPOSE 2024

# Run the LangGraph server
CMD ["uv", "run", "langgraph", "dev", "--host", "0.0.0.0", "--port", "2024", "--no-browser", "--allow-blocking"]
