# Deploy IndiaJob.in Today

## Option A — Docker (fastest, any VPS: DigitalOcean, AWS, Hostinger)

### 1. Get a VPS (₹500–800/month)
- DigitalOcean Droplet, AWS Lightsail, or Hostinger VPS
- Ubuntu 22.04, minimum 2GB RAM

### 2. Install Docker
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 3. Upload project & configure
```bash
git clone <your-repo> jobalert
cd jobalert
cp backend/.env.example backend/.env
nano backend/.env   # Set SECRET_KEY, ADMIN_SECRET, PUBLIC_SITE_URL, OPENAI_API_KEY, your domain
```

Generate secrets:
```bash
openssl rand -hex 32   # use for SECRET_KEY
openssl rand -hex 16   # use for ADMIN_SECRET
```

### 4. Deploy
```bash
docker compose up -d --build
```

Site live at: `http://YOUR_SERVER_IP:3000`

### 4b. Import existing database (optional)
If you copied `jobalert.db` to the server home directory, put it in the Docker volume:
```bash
docker compose up -d backend   # create volume + container name
docker compose cp ~/jobalert.db backend:/app/data/jobalert.db
docker compose restart backend
```

### Troubleshooting backend crash loop
```bash
# See why backend is restarting (most important)
docker compose logs backend --tail=100

# Config load test (works even when container is crash-looping)
docker compose run --rm --no-deps backend python -c "from app.config import settings; print(settings.cors_origins)"

# Health on the host
curl -s http://127.0.0.1:8000/health
```

Common fixes:
- **`ValidationError` on startup** — fix `backend/.env`; use comma-separated domains for `CORS_ORIGINS` if JSON fails, e.g. `CORS_ORIGINS=https://indiagovjob.online,https://www.indiagovjob.online`
- **OOM / killed** — ensure `SKIP_INITIAL_FETCH=1` in `docker-compose.yml` (default in repo), then `./jbcli fetch` manually after boot
- **502 from nginx** — backend must be healthy on port 8000; check `docker compose ps` shows `healthy`

### 5. Point domain (optional)
- Add A record: `yourdomain.com` → server IP
- Use Nginx reverse proxy + Let's Encrypt SSL (see below)

---

## Option B — Manual run on VPS

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env && nano .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Frontend
cd frontend
npm install && npm run build
npm start &
```

---

## Auto-fetch (automatic)

Runs every **60 minutes** automatically once backend starts.
Change interval in `.env`:
```
FETCH_INTERVAL_MINUTES=30
```

---

## Manual commands

### Fetch all government portals now
```bash
# Shell script
./fetch-jobs.sh

# Python CLI
cd backend && python -m app.cli fetch

# curl
curl -X POST http://localhost:8000/api/admin/fetch
```

### Upload a PDF notification
```bash
# Shell script
./upload-pdf.sh /path/to/notification.pdf
./upload-pdf.sh notice.pdf --state "Uttar Pradesh" --org UPPSC

# Python CLI
cd backend && python -m app.cli upload /path/to/notification.pdf

# curl
curl -X POST http://localhost:8000/api/admin/upload-pdf \
  -H "X-Admin-Key: your-admin-secret" \
  -F "file=@notification.pdf" \
  -F "state=Uttar Pradesh" \
  -F "organization=UPPSC"
```

### Web admin panel
Open: **http://yourdomain.com/admin**
- Upload PDFs via browser
- Click "Fetch All Jobs Now"
- Enter Admin Key if `ADMIN_SECRET` is set

---

## Nginx + SSL (production domain)

```nginx
server {
    listen 80;
    server_name indiajob.in www.indiajob.in;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }
}
```

Then:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d indiajob.in
```

---

## What happens when you upload a PDF

1. Text extracted from PDF
2. AI parses: title, department, state, category, last date, vacancies
3. Auto-categorized: Notification / Admit Card / Result / etc.
4. Published to website under correct state & department
5. Users with matching alert preferences get notified

---

## Checklist before going live

- [ ] Set `SECRET_KEY` and `ADMIN_SECRET` in `.env`
- [ ] Set `PUBLIC_SITE_URL` to your live domain (e.g. `https://indiagovjob.online`)
- [ ] Set `OPENAI_API_KEY` for best PDF parsing
- [ ] Update `CORS_ORIGINS` with your domain (or rely on `PUBLIC_SITE_URL` auto-merge)
- [ ] Point domain to server IP
- [ ] Enable SSL with Certbot
- [ ] Test: `./fetch-jobs.sh` and upload a PDF at `/admin`
