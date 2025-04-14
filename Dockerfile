FROM python:3.11-slim

WORKDIR /app

COPY app/ app/
COPY templates/ templates/

COPY requirements.txt .

COPY playbooks/ /srv/sdm/playbooks/

RUN apt-get update && \
    apt-get install -y curl dnsutils && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
