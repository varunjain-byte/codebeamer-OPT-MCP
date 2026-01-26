FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install CA certificates package
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY codebeamer_smart_tool.py .
COPY mcp_server.py .

# Copy custom certificates if provided (optional)
# Place your .crt files in ./certs/ folder before building
# Note: Create an empty certs/ folder if you don't have certificates
COPY certs/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates 2>/dev/null || true


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

# Also set REQUESTS_CA_BUNDLE for Python requests library
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Expose port
EXPOSE 8080

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the server
CMD ["python", "mcp_server.py"]

