#!/bin/bash

# Development startup script for Django Fish Recognition API

echo "Starting Django Fish Recognition API (Development)..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Database migrations
echo "Running database migrations..."
python manage.py makemigrations fish_recognition
python manage.py migrate

# Start development server
echo "Starting development server..."
python manage.py runserver 0.0.0.0:8000