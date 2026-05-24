FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install psycopg2-binary requests docker

WORKDIR /app
COPY failover.py .

CMD ["python", "-u", "failover.py"]
