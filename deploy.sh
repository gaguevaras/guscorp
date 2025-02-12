#!/bin/bash

echo "This will restart the web_prod service with a fresh build."
read -p "Are you sure you want to proceed? (y/N): " confirm

confirm=${confirm,,}

if [[ "$confirm" == "y" || "$confirm" == "yes" ]]; then
    echo "Starting deployment..."
    docker compose -f docker-compose.prod.yml up web_prod -d --force-recreate --build --remove-orphans
    echo "Deployment completed."
else
    echo "Operation cancelled."
fi
