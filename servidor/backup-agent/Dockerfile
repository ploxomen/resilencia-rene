FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    postgresql-client-15 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install psycopg2-binary requests

WORKDIR /app
COPY backup.py .

CMD ["python", "-u", "backup.py"]
