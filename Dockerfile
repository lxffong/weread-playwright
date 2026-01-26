FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chrome --with-deps

# Copy project files
COPY weread/ ./weread/
COPY main.py .

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
# Enable no-sandbox mode for Docker environment
ENV WEREAD_NO_SANDBOX=true

# Run the application
CMD ["python", "main.py"]
