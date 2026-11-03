FROM python:3.12-slim

# Install system dependencies (git is needed for worktree operations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official binary image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy project files and install dependencies
COPY clerk/pyproject.toml /app/clerk/
COPY clerk/src /app/clerk/src/
COPY config /app/config/

WORKDIR /app/clerk
RUN uv sync --no-dev

EXPOSE 8080

CMD ["uv", "run", "python", "-m", "clerk.cli", "serve", "--host", "0.0.0.0", "--port", "8080"]
