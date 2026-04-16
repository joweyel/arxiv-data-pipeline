FROM python:3.12-slim

# Adapted test Dockerfile from: https://docs.streamlit.io/deploy/tutorials/docker 

WORKDIR /app

COPY app.py requirements.txt ./

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv pip install -r requirements.txt --system

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]