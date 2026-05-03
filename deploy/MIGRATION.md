# Lush Temp Mail VPS migration

Script này dùng mô hình **cài mới code từ GitHub rồi migrate runtime data**. Nó không clone nguyên cả VPS và không ghi gì lên VPS nguồn.

## Script làm gì

- Clone hoặc reset repo `Lush-Temp-Mail` trên VPS mới.
- Copy `deploy/.env` từ VPS nguồn nếu có.
- Copy `deploy/data/` từ VPS nguồn, gồm SQLite database và dữ liệu app.
- Backup `deploy/data/` hiện có trên VPS mới trước khi ghi thêm dữ liệu.
- Tạo Docker network `shared_proxy` và `mailstack_default` nếu thiếu.
- Rebuild/start container `lushtempmail-app`.
- Kiểm tra `/api/health` bên trong container.

## Chuẩn bị

Trên VPS mới, cần SSH được vào VPS nguồn. Nên dùng SSH key thay vì password:

```bash
ssh-copy-id root@OLD_VPS_IP
```

Mailserver, MX, DKIM, Caddy và DNS không nằm trong script này. Phần đó nên setup riêng trước hoặc sau khi app chạy.

## Chạy migrate

```bash
cd /opt/lush-temp-mail/app
SOURCE_HOST=OLD_VPS_IP bash deploy/scripts/migrate_vps.sh
```

Nếu repo chưa có trên VPS mới, có thể tải script từ GitHub rồi chạy, nhưng cách dễ nhất vẫn là clone repo trước:

```bash
git clone https://github.com/shinemusicllc/Lush-Temp-Mail.git /opt/lush-temp-mail/app
cd /opt/lush-temp-mail/app
SOURCE_HOST=OLD_VPS_IP bash deploy/scripts/migrate_vps.sh
```

## Tùy biến thường dùng

```bash
SOURCE_HOST=OLD_VPS_IP \
SOURCE_USER=root \
SOURCE_APP_DIR=/opt/lush-temp-mail/app \
TARGET_APP_DIR=/opt/lush-temp-mail/app \
BRANCH=main \
bash deploy/scripts/migrate_vps.sh
```

Không copy `.env`:

```bash
SOURCE_HOST=OLD_VPS_IP SKIP_ENV=1 bash deploy/scripts/migrate_vps.sh
```

Không copy data:

```bash
SOURCE_HOST=OLD_VPS_IP SKIP_DATA=1 bash deploy/scripts/migrate_vps.sh
```

Chỉ chuẩn bị code/data, chưa start app:

```bash
SOURCE_HOST=OLD_VPS_IP START_APP=0 bash deploy/scripts/migrate_vps.sh
```

## Sau khi migrate

Kiểm tra container:

```bash
docker ps --filter name=lushtempmail-app
docker logs --tail 80 lushtempmail-app
docker exec lushtempmail-app python - <<'PY'
from urllib.request import urlopen
print(urlopen("http://127.0.0.1:8010/api/health", timeout=10).read().decode())
PY
```

Nếu dùng domain mới, cập nhật `deploy/.env` các biến mail/domain rồi rebuild:

```bash
cd /opt/lush-temp-mail/app
docker compose -f deploy/docker-compose.vps.yml --env-file deploy/.env up -d --build
```
