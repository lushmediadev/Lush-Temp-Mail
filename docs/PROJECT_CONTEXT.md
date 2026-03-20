# Project Context

- Project: `Lush-Temp-Mail`
- Current state: repo đã có backend FastAPI + SQLite + IMAP sync tại `backend/`, frontend admin shell ở root, lớp deploy VPS tại `deploy/`, và `.venv` local để chạy test/dev.
- Existing infrastructure dependency: VPS `82.197.71.6` đang chạy mail server cho `congmail.top`, hostname mail là `mail.congmail.top`, domain ứng dụng dự kiến là `lush.congmail.top`.
- Product goal: admin dashboard kiểu temp mail để quản lý nhiều địa chỉ `@congmail.top`, xem mail theo từng alias, copy email, đọc OTP/link nhanh, lọc theo service, auto expire/delete alias.
- Key requirement: người dùng có thể nhập trực tiếp một địa chỉ bất kỳ như `abc123@congmail.top` trên site khác mà vẫn nhận mail, không cần vào app để tạo alias trước.
- Mail runtime direction: mail server live đã bật catch-all `@congmail.top -> contact@congmail.top`; app backend đọc IMAP từ mailbox trung tâm rồi auto-discover alias mới từ inbound mail thật.
- VPS runtime status: app container đang chạy trên `127.0.0.1:8012`, Caddy chung trên VPS đã có route nội bộ cho `lush.congmail.top`, nhưng DNS public cho subdomain này vẫn cần trỏ về `82.197.71.6` để lấy cert/public access.
- Ops helper status: VPS đã có helper `lushtempmail`, và script `lushtempmail set-admin` dùng để đổi `ADMIN_USERNAME` / `ADMIN_PASSWORD` trong `deploy/.env` rồi redeploy app.
