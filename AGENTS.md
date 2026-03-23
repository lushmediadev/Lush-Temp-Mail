## Working agreements

- Khi giao tiếp, trả lời, walkthrough, task/checklist, hướng dẫn triển khai: viết tiếng Việt.
- Giữ nguyên tiếng Anh cho: tên hàm/biến, log lỗi, lệnh terminal, config key, API field.
- Luôn phân loại nhiệm vụ thành `Quick Task` hoặc `Project Task` trước khi thực hiện.

## Build / Test / Run

- Dev server: chạy từ root repo với `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010 --reload`
- Tests: chạy từ root repo với `.\.venv\Scripts\python.exe -m pytest -q`
- Python syntax check: chạy từ root repo với `Get-ChildItem .\backend\app\*.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }`
- Frontend syntax check: chạy từ root repo với `node --check .\app.js`
- VPS helper usage: `lushtempmail status|logs|redeploy|update`

## Coding Conventions

- Giữ diff nhỏ, ưu tiên nối backend vào UI hiện có thay vì thay toàn bộ layout.
- Preserve vanilla HTML/CSS/JS ở root; không thêm bundler nếu chưa thật sự cần.
- Text tiếng Việt trong file source phải lưu UTF-8 chuẩn, không để mojibake.
- API phải tối ưu cho luồng temp-mail admin: alias list, inbox by alias, OTP/link extraction, expire/delete.

## UI Discipline

- Mọi task tạo mới/chỉnh sửa/polish UI trong repo này đều phải dùng skill `uncodixfy`.
- Trước khi sửa UI, phải đọc các file giao diện hiện có liên quan (`index.html`, `user.html`, `app.js`, `user.js`, `style.css`, `user.css`) để bám đúng visual language đang dùng.
- Ưu tiên sửa trực tiếp theo pattern hiện hữu của app; không tự thêm nested cards, floating cards, detached panels, hero sections, hoặc ornamental badges nếu UI hiện tại không dùng.
- Nếu một thay đổi UI không thể bám theo pattern sẵn có, phải nêu rõ lý do và giới hạn phạm vi khác biệt.

## Subagent Use

- Trước mỗi `Project Task`, phải tự đánh giá rõ có nên spawn subagent hay không và dựa trên tính độc lập thực sự của phần việc.
- Trong repo này, ưu tiên dùng subagent cho exploration/read-only investigation hơn là implementation.
- Không giao phần edit code/file cho subagent theo mặc định khi main agent có thể xử lý trực tiếp mà không bị chặn.
- Chỉ spawn khi có ít nhất hai đầu việc độc lập, có thể chạy song song, và không gây trùng lặp với luồng chính.
- Việc spawn phải tuân theo policy/tooling hiện hành; nếu không nên hoặc không được phép, phải ghi rõ quyết định giữ toàn bộ implementation ở luồng chính.

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
