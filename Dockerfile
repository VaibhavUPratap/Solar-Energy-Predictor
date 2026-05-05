# Use an official lightweight Python image
FROM python:3.10-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE=1 prevents Python from writing .pyc files
# PYTHONUNBUFFERED=1 ensures logs are sent straight to terminal (e.g. your container log) without being first buffered
# PORT=10000 sets the default port that gunicorn will use
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Upgrade pip and install the dependencies
# --no-cache-dir keeps the image smaller by not caching the downloaded packages
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files into the working directory
COPY . .

# Expose the port the app runs on
EXPOSE 10000

# Command to run the application using Gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
