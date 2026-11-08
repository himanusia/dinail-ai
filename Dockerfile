FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dinail_ai ./dinail_ai
ENV DINAIL_SIZE_TABLE=/app/dinail_ai/size_table.json
EXPOSE 8000
CMD ["uvicorn", "dinail_ai.app:app", "--host", "0.0.0.0", "--port", "8000"]
