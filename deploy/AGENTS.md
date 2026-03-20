## Deploy Rules

- Deploy stack của repo này chỉ phụ trách app `lush.congmail.top`; không tự ý bind trực tiếp `80/443` vì VPS đã có Caddy chung.
- Port host mặc định là `127.0.0.1:8012 -> container 8010`.
- Password IMAP/admin thật chỉ tồn tại trong `.env` trên VPS, không commit.

## Commands

- VPS compose: `cd /opt/lush-temp-mail/app/deploy && docker compose --env-file .env -f docker-compose.vps.yml up -d --build`
- Helper usage: `lushtempmail status|logs|redeploy|update`
