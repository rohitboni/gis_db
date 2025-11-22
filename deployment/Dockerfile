FROM python:3.11-slim

# Install system dependencies for PostGIS/GeoAlchemy
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    binutils \
    postgresql-client \
    python3-gdal \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for GeoDjango/GeoAlchemy
ENV GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/

# Install Python dependencies (excluding GDAL - using system version)
RUN pip install --no-cache-dir -r requirements.txt

# Create symlink for system GDAL Python bindings
RUN ln -s /usr/lib/python3/dist-packages/osgeo /usr/local/lib/python3.11/site-packages/osgeo || true

# Copy application code
COPY . .

EXPOSE 8000

# Run FastAPI application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
