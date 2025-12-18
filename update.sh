#!/bin/bash
git pull origin main
sudo docker rm -f moviespace
sudo docker build -t moviespace-image .
sudo docker run -d \
  --name moviespace \
  -p 127.0.0.1:8081:8080 \
  --env-file .env \
  --restart always \
  -v $(pwd)/data:/app/data \
  moviespace-image
echo "🚀 MovieSpace is succesvol geüpdatet!"
