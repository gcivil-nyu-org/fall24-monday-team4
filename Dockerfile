# Use Ubuntu as the base image
FROM ubuntu:latest

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Update and install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-contrib \
    postgis \
    libgeos-dev \
    libproj-dev \
    libgdal-dev \
    libffi-dev \
    software-properties-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add deadsnakes PPA to get Python 3.12
RUN add-apt-repository ppa:deadsnakes/ppa

# Install Python 3.12 and pip
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3-pip \
    python-is-python3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy the project code into the container
COPY . .

# Expose the port your app runs on
EXPOSE 5000

# Command to run the application
CMD ["python3", "manage.py", "runserver", "0.0.0.0:5000"]
