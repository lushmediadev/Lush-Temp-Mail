## Working agreements

- Khi giao tiếp, trả lời, walkthrough, task/checklist, hướng dẫn triển khai: viết tiếng Việt.
- Giữ nguyên tiếng Anh cho: tên hàm/biến, log lỗi, lệnh terminal, config key, API field.
- Luôn phân loại nhiệm vụ thành `Quick Task` hoặc `Project Task` trước khi thực hiện.

## Build / Test / Run

- Dev server: `cd D:\Lush-Temp-Mail && .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010 --reload`
- Tests: `cd D:\Lush-Temp-Mail && .\.venv\Scripts\python.exe -m pytest -q`
- Python syntax check: `python -m py_compile D:\Lush-Temp-Mail\backend\app\*.py`
- Frontend syntax check: `node --check D:\Lush-Temp-Mail\app.js`
- VPS helper usage: `lushtempmail status|logs|redeploy|update`

## Coding Conventions

- Giữ diff nhỏ, ưu tiên nối backend vào UI hiện có thay vì thay toàn bộ layout.
- Preserve vanilla HTML/CSS/JS ở root; không thêm bundler nếu chưa thật sự cần.
- Text tiếng Việt trong file source phải lưu UTF-8 chuẩn, không để mojibake.
- API phải tối ưu cho luồng temp-mail admin: alias list, inbox by alias, OTP/link extraction, expire/delete.

## Module Boundaries

- Root static files (`index.html`, `app.js`, `style.css`, `logo.svg`) chịu trách nhiệm UI/admin shell.
- `backend/` chịu trách nhiệm auth, mail sync, alias/message persistence, OTP/link extraction.
- `deploy/` chịu trách nhiệm runtime VPS và helper scripts.
- Mail server/runtime config thuộc VPS mail stack hiện có; repo này chỉ gọi integration layer cần thiết.

## Debug Workflow

- Reproduce trên local UI trước, sau đó test lại bằng API thực.
- Với luồng email, luôn xác minh đủ 3 bước: sync inbox, parse recipient alias, extract OTP/link.
- Khi sửa frontend JS, luôn kiểm tra login flow, alias list, email detail, copy action.

## Regression Checklist

- Admin vẫn đăng nhập được sau khi đổi session/auth code.
- Alias có thể được tạo thủ công và cũng tự xuất hiện khi mail gửi vào địa chỉ chưa pre-create.
- Email detail hiển thị đúng recipient, sender, subject, body, OTP, links.
- Delete/expire alias không làm hỏng lịch sử alias khác.

## Refactor Safety

- Không đổi contract API đã dùng bởi frontend nếu chưa cập nhật đồng bộ app.js.
- Không buộc người dùng phải pre-create alias trước khi nhận mail; đây là yêu cầu cốt lõi.
- Không chỉnh phá mail stack `congmail.top` hiện đang hoạt động nếu chưa có rollback rõ ràng.
