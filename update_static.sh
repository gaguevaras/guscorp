#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

LOG_FILE="/var/log/static_update.log"
exec > >(tee -a $LOG_FILE) 2>&1  # Log output

echo "Starting static file collection..."

echo "Running Django collectstatic inside Docker..."
if docker compose -f docker-compose.prod.yml exec web_prod python manage.py collectstatic --noinput; then
    echo "✔ Django collectstatic completed successfully."
else
    echo "❌ Failed to run collectstatic. Check the logs." >&2
    exit 1
fi

echo "Setting correct ownership for static files..."
if sudo chown -R www-data:www-data /home/gus/guscorp/staticfiles; then
    echo "✔ Ownership set successfully."
else
    echo "❌ Failed to set ownership." >&2
    exit 1
fi

echo "Setting correct permissions for static files..."
if sudo chmod -R 755 /home/gus/guscorp/staticfiles; then
    echo "✔ Permissions set successfully."
else
    echo "❌ Failed to set permissions." >&2
    exit 1
fi

echo "Ensuring directory traversal permissions..."
if sudo chmod +x /home/gus /home/gus/guscorp; then
    echo "✔ Directory traversal permissions set successfully."
else
    echo "❌ Failed to set directory permissions." >&2
    exit 1
fi

echo "All operations completed successfully!"
