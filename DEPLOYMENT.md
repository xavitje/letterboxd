# 🚀 MovieSpace VPS Deployment Guide

## 📋 Stappenplan voor Docker Deployment op VPS

### Stap 1: Voorbereiding Lokaal (Windows)

1. **Zorg dat alle bestanden klaar zijn:**
   ```powershell
   # Test of alles lokaal werkt
   python main.py
   ```

2. **Maak een .dockerignore bestand:**
   ```
   __pycache__
   *.pyc
   *.pyo
   *.db
   .git
   .env
   venv
   env
   .vscode
   ```

### Stap 2: Upload naar VPS

**Optie A: Via Git (aanbevolen)**
```bash
# Op je lokale machine
git init
git add .
git commit -m "Initial commit"
git remote add origin <jouw-git-repo-url>
git push -u origin main

# Op VPS
cd /opt
sudo git clone <jouw-git-repo-url> moviespace
cd moviespace
```

**Optie B: Via SCP/SFTP**
```powershell
# Op Windows (PowerShell)
scp -r C:\Users\rafie\Letterbox user@your-vps-ip:/opt/moviespace
```

### Stap 3: VPS Setup

1. **SSH naar je VPS:**
   ```bash
   ssh user@your-vps-ip
   ```

2. **Installeer Docker (als nog niet geïnstalleerd):**
   ```bash
   # Update systeem
   sudo apt update && sudo apt upgrade -y

   # Installeer Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Installeer Docker Compose
   sudo apt install docker-compose -y

   # Voeg gebruiker toe aan docker groep
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **Navigeer naar project directory:**
   ```bash
   cd /opt/moviespace
   ```

4. **Configureer .env bestand:**
   ```bash
   sudo nano .env
   ```

   Zorg dat je .env bestand dit bevat:
   ```env
   TMDB_API_KEY=jouw_tmdb_api_key
   SECRET_KEY=jouw_secret_key
   DATABASE_URL=sqlite:////app/data/moviespace.db
   ```

5. **Maak data directory:**
   ```bash
   mkdir -p data
   sudo chown -R $USER:$USER data
   ```

### Stap 4: Build en Start Docker Container

```bash
# Build de Docker image
docker-compose build

# Start de container
docker-compose up -d

# Check of container draait
docker-compose ps
docker-compose logs -f
```

### Stap 5: Nginx Reverse Proxy Setup

1. **Installeer Nginx (als nog niet geïnstalleerd):**
   ```bash
   sudo apt install nginx -y
   ```

2. **Maak Nginx configuratie:**
   ```bash
   sudo nano /etc/nginx/sites-available/movie.drissi.store
   ```

   Kopieer de inhoud van `nginx-config.conf` hierin.

3. **Activeer de site:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/movie.drissi.store /etc/nginx/sites-enabled/
   ```

4. **Test Nginx configuratie:**
   ```bash
   sudo nginx -t
   ```

5. **Herstart Nginx:**
   ```bash
   sudo systemctl restart nginx
   ```

### Stap 6: DNS Configuratie

1. Ga naar je DNS provider (waar drissi.store wordt gehost)
2. Voeg een A-record toe:
   - **Type:** A
   - **Name:** movie
   - **Value:** Je VPS IP-adres
   - **TTL:** 3600 (of auto)

3. Wacht 5-15 minuten voor DNS propagatie

4. Test DNS:
   ```bash
   nslookup movie.drissi.store
   ```

### Stap 7: SSL Certificate (HTTPS) - Optioneel maar aanbevolen

1. **Installeer Certbot:**
   ```bash
   sudo apt install certbot python3-certbot-nginx -y
   ```

2. **Verkrijg SSL certificaat:**
   ```bash
   sudo certbot --nginx -d movie.drissi.store
   ```

3. **Volg de prompts:**
   - Voer je email in
   - Accepteer Terms of Service
   - Kies optie 2 (Redirect HTTP to HTTPS)

4. **Auto-renewal test:**
   ```bash
   sudo certbot renew --dry-run
   ```

### Stap 8: Verificatie

1. **Test de applicatie:**
   ```bash
   curl http://localhost:8080
   curl http://movie.drissi.store
   ```

2. **Open in browser:**
   - http://movie.drissi.store (zonder SSL)
   - https://movie.drissi.store (met SSL)

### Stap 9: Beheer Commands

```bash
# Stop containers
docker-compose down

# Start containers
docker-compose up -d

# Bekijk logs
docker-compose logs -f moviespace

# Herstart container
docker-compose restart

# Update applicatie (na code wijzigingen)
git pull
docker-compose build
docker-compose up -d

# Backup database
cp data/moviespace.db data/moviespace.db.backup

# Clean up Docker
docker system prune -a
```

### Stap 10: Firewall Configuratie

```bash
# Als je ufw gebruikt
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
sudo ufw status
```

## 🔧 Troubleshooting

**Container start niet:**
```bash
docker-compose logs moviespace
```

**Nginx errors:**
```bash
sudo tail -f /var/log/nginx/error.log
```

**Poort conflicten:**
```bash
# Check welke poorten in gebruik zijn
sudo netstat -tulpn | grep :8080
```

**Database issues:**
```bash
# Reset database
docker-compose down
rm -rf data/moviespace.db
docker-compose up -d
```

## 📊 Monitoring

**Check resource gebruik:**
```bash
docker stats moviespace
```

**Check logs:**
```bash
docker-compose logs -f --tail=100 moviespace
```

## 🔄 Updates

```bash
# Pull nieuwe code
cd /opt/moviespace
git pull

# Rebuild en herstart
docker-compose down
docker-compose build
docker-compose up -d
```

## ✅ Checklist

- [ ] Docker geïnstalleerd
- [ ] Code op VPS
- [ ] .env bestand geconfigureerd
- [ ] Docker container draait
- [ ] Nginx geïnstalleerd en geconfigureerd
- [ ] DNS A-record toegevoegd
- [ ] SSL certificaat (optioneel)
- [ ] Firewall geconfigureerd
- [ ] Applicatie toegankelijk via movie.drissi.store

## 🎉 Klaar!

Je MovieSpace applicatie is nu live op: https://movie.drissi.store
