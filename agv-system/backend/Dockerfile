
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Library
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào container
COPY . /app/