# Decisions

Decision | Reason | Impact | Date
--- | --- | --- | ---
Bootstrap repo rules/docs trước khi thêm backend | Repo mới chưa có AGENTS/docs nhưng task sẽ gồm nhiều bước và deploy thật | Có nơi lưu context/quy ước trước khi triển khai code | 2026-03-20
Chọn kiến trúc `FastAPI + SQLite + IMAP sync` thay vì mailbox-per-alias | Phù hợp nhất với yêu cầu catch-all nhận mọi địa chỉ bất kỳ mà không cần pre-create alias trước | Backend chỉ cần đọc inbox trung tâm, tự phát hiện alias mới và group mail theo recipient | 2026-03-20
Triển khai app trên VPS qua `127.0.0.1:8012` sau Caddy chung | VPS đã có Caddy chiếm `80/443`, nên app mới không nên bind trực tiếp public ports | Giảm xung đột runtime, chỉ cần thêm một block `lush.congmail.top` vào Caddy hiện có | 2026-03-20
Quản lý admin login của `Lush Temp Mail` qua helper script | Tránh sửa tay `deploy/.env` trên VPS và quên redeploy sau khi đổi credential | Có lệnh vận hành rõ ràng `lushtempmail set-admin`, dễ ghi vào cheat sheet | 2026-03-20
Cho app temp-mail join Docker network `mailstack_default` để đọc IMAP trực tiếp từ mailserver container | Đường host/public cho `mail.congmail.top` trên VPS gây sync fail dù mail đã vào inbox trung tâm | Deploy phải giữ `mailstack_default` và `IMAP_HOST=mail.congmail.top` để catch-all mailbox luôn được import ổn định | 2026-03-20
