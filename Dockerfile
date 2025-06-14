# Use a base image with Python pre-installed
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed for decompression
# Install system dependencies needed for Blender and decompression
RUN apt-get update && apt-get install -y \
    xz-utils \
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
    && rm -rf /var/lib/apt/lists/*

# Install Blender
# Download and extract a specific version of Blender for Linux
# You can change the version to match what you used in development
ADD https://mirror.clarkson.edu/blender/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz /tmp/
RUN tar -xvf /tmp/blender-4.0.2-linux-x64.tar.xz -C /usr/local/ && \
    rm /tmp/blender-4.0.2-linux-x64.tar.xz

# Add Blender to the system's PATH
ENV PATH="/usr/local/blender-4.0.2-linux-x64:${PATH}"

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Set the entrypoint to run your main script
ENTRYPOINT ["python", "src/tile_gen.py"]

# Set a default command (can be overridden)
CMD ["-a", "all"]