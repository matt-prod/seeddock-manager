FROM python:3.11-slim

WORKDIR /app

COPY app/ app/
COPY templates/ templates/
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
