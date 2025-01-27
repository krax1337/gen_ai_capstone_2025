FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY . .

RUN uv sync --frozen

EXPOSE 3434

CMD ["uv", "run", "streamlit", "run", "main.py", "--server.port", "3434", "--server.address=0.0.0.0"]