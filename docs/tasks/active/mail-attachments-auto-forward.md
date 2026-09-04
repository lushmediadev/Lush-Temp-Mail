# mail-attachments-auto-forward

## Goal
- Hỗ trợ đính kèm tệp khi soạn, trả lời và chuyển tiếp email.
- Tự động chuyển tiếp thư mới của alias được chọn tới một địa chỉ email ngoài hệ thống.

## Scope
- `backend/app/db.py`, `backend/app/imap_sync.py`, `backend/app/mailer.py`, `backend/app/main.py`.
- `index.html`, `app.js`, `style.css` và test liên quan.

## Constraints
- Không thay đổi mailserver hoặc làm gián đoạn nhận mail hiện tại.
- Không forward thư cũ trước thời điểm tạo rule và không forward trùng khi IMAP sync lại.
- Nâng SMTP `message_size_limit` lên 30 MB và giới hạn tệp gốc 18 MB để phù hợp mức tăng do MIME/base64.

## Current State
- Đã xác định IMAP IDLE lưu attachment payload trong SQLite và SMTP sender dùng central mailbox làm envelope.
- Đang bổ sung schema delivery idempotency và API quản lý rule.

## Next Steps
- Hoàn thiện backend, UI, test local, rồi deploy riêng app container.

## Risks
- Vòng lặp forwarding nếu destination thuộc cùng domain; sẽ giới hạn destination ngoài `@lushmedia.net`.
- MIME base64 làm kích thước email lớn hơn file gốc; tổng file giới hạn 18 MB để tránh vượt ngưỡng Gmail 25 MB.
