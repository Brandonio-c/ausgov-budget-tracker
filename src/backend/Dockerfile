FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

COPY . /app/backend

EXPOSE 8010

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "2"]
