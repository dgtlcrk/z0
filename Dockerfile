FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY z0 ./z0

RUN useradd --create-home --uid 10001 z0
USER z0

CMD ["python", "-m", "z0.main"]
