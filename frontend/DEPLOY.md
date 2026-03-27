# Deploy — Wandi Frontend on VPS

## Prerequisites

- VPS with Nginx installed
- Node.js 18+ installed
- Domain pointed to VPS IP (e.g., `app.gayafinkhaelyon.online`)

## 1. Build

```bash
cd ~/wandi-agent/frontend
cp .env.example .env
# Edit .env with production values
npm install
npm run build
```

## 2. Copy dist to Nginx

```bash
sudo mkdir -p /var/www/wandi-frontend
sudo cp -r dist/* /var/www/wandi-frontend/
```

## 3. Nginx config

Create `/etc/nginx/sites-available/wandi-frontend`:

```nginx
server {
    listen 80;
    server_name app.gayafinkhaelyon.online;

    root /var/www/wandi-frontend;
    index index.html;

    # SPA fallback — all routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/wandi-frontend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 4. SSL with Let's Encrypt

```bash
sudo certbot --nginx -d app.gayafinkhaelyon.online
```

## 5. Supabase Auth — Add Redirect URL

In Supabase Dashboard → Authentication → URL Configuration:

- Add `https://app.gayafinkhaelyon.online` to **Site URL**
- Add `https://app.gayafinkhaelyon.online/**` to **Redirect URLs**

## 6. Update on new builds

```bash
cd ~/wandi-agent/frontend
git pull
npm install
npm run build
sudo cp -r dist/* /var/www/wandi-frontend/
```

No Nginx restart needed — just overwrite the files.
