FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        iputils-ping \
        traceroute \
        whois && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY z0 ./z0

RUN useradd --create-home --uid 10001 z0

USER z0

CMD ["python", "-m", "z0.main"]
