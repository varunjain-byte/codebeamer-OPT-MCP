FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY codebeamer_smart_tool.py .
COPY mcp_server.py .

# Create non-root user for security (OpenShift requirement)
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# Environment variables (override at runtime)
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080
ENV CODEBEAMER_URL=https://your-codebeamer.com
ENV CODEBEAMER_API_KEY=""
ENV CODEBEAMER_SSL_VERIFY=true
ENV CODEBEAMER_MAX_CALLS=60
ENV CODEBEAMER_CACHE_TTL=300

# Expose port
EXPOSE 8080

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the server
CMD ["python", "mcp_server.py"]
