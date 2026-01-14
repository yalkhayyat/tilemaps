# Use a base image with Python pre-installed
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed for libraries
RUN apt-get update && apt-get install -y \
    libx11-6 \
    libxxf86vm1 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libgl1 \
    libxkbcommon0 \
    libgomp1 \
    libsm6 \
    libice6 \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Set the entrypoint to run your main script
ENTRYPOINT ["python", "main.py"]

# Set a default command (can be overridden)
CMD ["--asset", "all"]