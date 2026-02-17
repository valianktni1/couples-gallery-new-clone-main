# Dockge Deployment Guide - Couples Gallery

## Prerequisites
- TrueNAS with Dockge installed
- GitHub repository pushed with latest code
- Folders created on TrueNAS:
  - `/mnt/apps/newweddingsbymarkgallery/db`
  - `/mnt/apps/newweddingsbymarkgallery/thumbnails`
  - `/mnt/apps/newweddingsbymarkgallery/previews`
  - `/mnt/nextcloud/newwedidngsbymarkuserfiles`

## Steps

### 1. Push Latest Code to GitHub
In GitHub Desktop:
1. Commit all changes with message: "Deploy storage refactor fixes"
2. Push to origin

### 2. Create Stack in Dockge
1. Open Dockge UI
2. Click **"+ Compose"** (or equivalent)
3. Name it: `couples-gallery`
4. Paste the docker-compose content below

### 3. Docker Compose Configuration
Copy this entire block into Dockge:

```yaml
version: "3.8"

services:
  mongodb-db:
    image: mongo:7.0
    container_name: gallery-db-v3
    restart: unless-stopped
    volumes:
      - /mnt/apps/newweddingsbymarkgallery/db:/data/db
    networks:
      - gallery-network
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s

  backend-api:
    build:
      context: https://github.com/valianktni1/couples-gallery-new-clone-main.git#main:backend
      dockerfile: Dockerfile
    container_name: gallery-api-v3
    restart: unless-stopped
    depends_on:
      mongodb-db:
        condition: service_healthy
    volumes:
      - /mnt/apps/newweddingsbymarkgallery/thumbnails:/app/data/thumbnails
      - /mnt/apps/newweddingsbymarkgallery/previews:/app/data/previews
      - /mnt/nextcloud/newwedidngsbymarkuserfiles:/app/files
    environment:
      - MONGO_URL=mongodb://mongodb-db:27017
      - DB_NAME=couples_gallery
      - JWT_SECRET=Valiant-kni123456
      - FILES_DIR=/app/files
      - DATA_DIR=/app/data
    networks:
      - gallery-network
    # Enable interactive console
    tty: true
    stdin_open: true
    healthcheck:
      test: curl -f http://localhost:8001/api/setup/status || exit 1
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 15s

  frontend-web:
    build:
      context: https://github.com/valianktni1/couples-gallery-new-clone-main.git#main:frontend
      dockerfile: Dockerfile
      args:
        - REACT_APP_BACKEND_URL=
    container_name: gallery-web-v3
    restart: unless-stopped
    depends_on:
      backend-api:
        condition: service_healthy
    networks:
      - gallery-network

  nginx-gateway:
    image: nginx:alpine
    container_name: gallery-gateway-v3
    restart: unless-stopped
    depends_on:
      backend-api:
        condition: service_healthy
      frontend-web:
        condition: service_started
    ports:
      - 3037:80
    command: >
      /bin/sh -c "sleep 5; printf 'server { listen 80; location /api/ {
      proxy_pass http://backend-api:8001; proxy_set_header Host \044host;
      proxy_set_header X-Real-IP \044remote_addr; } location / { proxy_pass
      http://frontend-web:3000; proxy_set_header Host \044host; proxy_set_header
      Upgrade \044http_upgrade; proxy_set_header Connection \"upgrade\"; } }' >
      /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
    networks:
      - gallery-network

networks:
  gallery-network:
    driver: bridge
```

### 4. Deploy
1. Click **"Deploy"** or **"Start"**
2. Wait for all containers to build and start (this may take 5-10 minutes on first build)
3. Watch the logs for any errors

### 5. Run Migration (IMPORTANT!)
After containers are running:
1. In Dockge, select the `backend-api` container
2. Open the **Console/Terminal**
3. Run: `python backend/migrate_storage.py`
4. Wait for migration to complete

### 6. Access Your Gallery
Open browser to: `http://your-truenas-ip:3037`

## Troubleshooting

**If containers fail to start:**
- Check Dockge logs for specific errors
- Verify all volume paths exist on TrueNAS
- Ensure port 3037 is not already in use

**If files don't appear:**
- Verify migration script ran successfully
- Check `/mnt/nextcloud/newwedidngsbymarkuserfiles` has correct permissions

**To rebuild after code changes:**
1. Push new code to GitHub
2. In Dockge, click **"Update"** or **"Rebuild"**
