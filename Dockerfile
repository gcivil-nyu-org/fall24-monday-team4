# Use Ubuntu as the base image
FROM ubuntu:latest

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Add deadsnakes PPA first, then do all apt-get operations in one layer
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
        postgis \
        libgeos-dev \
        libproj-dev \
        libgdal-dev \
        libffi-dev \
        python3.12 \
        python3-pip \
        python-is-python3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
    
# Set the working directory earlier
WORKDIR /app

# Copy only requirements first (better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy the project code and entrypoint script
COPY . .
COPY entrypoint.sh /

# Expose port
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["sh", "/entrypoint.sh"]
# Command to run the application
# CMD ["gunicorn", "routepals.wsgi:application", "-b", "0.0.0.0:5000"]
# CMD ["python3", "manage.py", "runserver", "0.0.0.0:5000"]