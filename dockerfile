# Use an official Python image as a base
FROM python:3.9-slim

# Set the working directory to /app
WORKDIR /app

# Install GDAL and its dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libsqlite3-dev \
    libspatialindex-dev \
    postgresql-client \
    netcat-openbsd \
    iputils-ping \
    telnet

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .