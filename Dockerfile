FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.simulator.txt .
RUN pip install --no-cache-dir -r requirements.simulator.txt

COPY simulator.py .

ENTRYPOINT ["python", "simulator.py"]
