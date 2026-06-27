FROM python:3.11-slim

COPY src /app

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt

CMD ["python3", "main.py"]
