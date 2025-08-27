FROM python:3.12.8-slim

WORKDIR /app

COPY ./pyproject.toml ./pyproject.toml
COPY ./README.md ./README.md
COPY ./src ./src

RUN pip install --no-cache-dir . gunicorn

EXPOSE 8000

CMD ["gunicorn", "src.server:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "300"]
