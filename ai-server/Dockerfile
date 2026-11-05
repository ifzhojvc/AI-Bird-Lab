FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY ai-server/requirements.txt ./ai-server/requirements.txt
RUN pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r ai-server/requirements.txt
COPY birdlab ./birdlab
COPY ai-server ./ai-server
COPY data/birds.json ./data/birds.json
ENV BIRD_DEVICE=cpu
ENV BIRD_OFFLINE=false
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--app-dir", "ai-server", "--host", "0.0.0.0", "--port", "8000"]
