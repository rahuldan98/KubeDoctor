FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv --no-cache-dir

# Point uv cache to /tmp so it's always writable (no root home needed)
ENV UV_CACHE_DIR=/tmp/.cache/uv

# Copy dependency files first for Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies only — skip the local package (src/ not copied yet).
# This layer is cached as long as pyproject.toml / uv.lock don't change.
RUN uv sync --no-dev --frozen --no-install-project

# Copy source code and README (required by uv-build — pyproject.toml references it)
COPY README.md ./
COPY src/ ./src/

# Now install the local kubedoctor package itself
RUN uv sync --no-dev --frozen

EXPOSE 8000

# Run server using uv virtualenv without re-syncing at runtime
CMD ["uv", "run", "--no-sync", "python", "src/kubedoctor/server.py"]
