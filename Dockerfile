FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py endpoints.py openapi.yaml utils.py ./

EXPOSE 6066

CMD ["faust", "-A", "app", "worker", "-l", "info"]
