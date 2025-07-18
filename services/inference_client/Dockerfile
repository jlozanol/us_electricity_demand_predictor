# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install the project into /app
WORKDIR /app

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Add the rest of the project source code and install it
# Installing separatedly from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Then, use a final image without uv
FROM python:3.12-slim-bookworm
# It is important to use the image that matches the builder, as the path to the
# Python executable must be the same

WORKDIR /app

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# Copy environment files
COPY .env ./

RUN mkdir -p /app/model_artifacts
COPY model_artifacts/* /app/model_artifacts/


# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["streamlit", "run", "/app/src/main.py"]