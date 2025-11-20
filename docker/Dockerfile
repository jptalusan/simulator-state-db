FROM python:3.13.7-slim
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

WORKDIR /usr/src
# Copy dependency files explicitly (better cache usage)
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

CMD ["uv", "run", "fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8050" ]