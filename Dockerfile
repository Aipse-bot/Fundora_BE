# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster # Or your preferred Python version

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
# This copies everything from your local project directory to the /app directory in the container
COPY . /app/

# Expose the port Gunicorn will listen on
# Render typically maps its own port, but exposing 8000 is standard practice
EXPOSE 8000

# Command to run your application using Gunicorn
# Replace 'your_project_name' with the actual name of your Django project's directory
# The --bind 0.0.0.0:8000 ensures Gunicorn listens on all available network interfaces within the container on port 8000.
# Render will then map its assigned port to this container port.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "fundora_backend.wsgi:application"]