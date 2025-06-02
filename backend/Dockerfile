# Use an official Python runtime as a parent image
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="/root/.pulumi/bin:$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    # Add any other system dependencies your project might need
    && rm -rf /var/lib/apt/lists/*

# Install Pulumi CLI
# This script typically installs Pulumi to $HOME/.pulumi/bin
RUN curl -fsSL https://get.pulumi.com | sh

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set workdir
WORKDIR /app

# Copy only files necessary for dependency installation first
COPY poetry.lock pyproject.toml ./

# Install project dependencies (including the pulumi Python SDK)
RUN poetry install --no-interaction --no-ansi

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on (for FastAPI)
EXPOSE 8000

# The CMD will be set in docker-compose.yml for each service (api, worker, beat)