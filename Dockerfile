# FHL Bible MCP Server - Dockerfile for Smithery.ai
# https://smithery.ai/docs/build/deployments/custom-container

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TRANSPORT=http

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Smithery uses PORT 8081
ENV PORT=8081
EXPOSE 8081

# Run the MCP server in HTTP mode
CMD ["python", "-m", "fhl_bible_mcp.http_server"]

