FROM python:3.11-slim

WORKDIR /app

RUN pip install torch --index-url https://download.pytorch.org/whl/cpu --no-cache-dir

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
