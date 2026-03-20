from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .auth import clear_admin_session, create_admin_session, require_admin
from .config import settings
from .imap_sync import MailSyncService
from .mailer import send_composed_message
from .translator import DEFAULT_TARGET_LANGUAGE, translate_message
from .utils import iso_in_hours, is_valid_local_part, random_local_part


mail_sync = MailSyncService()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    mail_sync.start()
    yield
    mail_sync.stop()


app = FastAPI(title="Lush Temp Mail", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url, f"https://{settings.public_domain}", "http://127.0.0.1:8010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "mail_domain": settings.mail_domain, "public_domain": settings.public_domain}


@app.post("/api/auth/login")
def login(response: Response, payload: dict[str, str] = Body(...)) -> dict[str, Any]:
    username = payload.get("email", "").strip()
    password = payload.get("password", "")
    if username != settings.admin_username or password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")
    session = create_admin_session(response)
    return {"ok": True, "user": {"username": session["username"], "role": "admin"}, "expires_at": session["expires_at"]}


@app.post("/api/auth/logout")
def logout(response: Response, session=Depends(require_admin)) -> dict[str, bool]:
    clear_admin_session(response, session["token"])
    return {"ok": True}


@app.get("/api/auth/session")
def session(session=Depends(require_admin)) -> dict[str, Any]:
    return {"ok": True, "user": {"username": session["username"], "role": "admin"}, "expires_at": session["expires_at"]}


@app.get("/api/mailboxes")
def list_mailboxes(
    status: str = Query("visible"),
    search: str = Query(""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    return {"items": db.list_aliases(search=search, status=status)}


@app.post("/api/mailboxes")
def create_mailbox(payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    requested_local_part = (payload.get("local_part") or "").strip().lower()
    label = (payload.get("label") or "").strip() or None
    expires_in_hours = int(payload.get("expires_in_hours") or settings.default_alias_hours)

    if requested_local_part:
        if not is_valid_local_part(requested_local_part):
            raise HTTPException(status_code=400, detail="local_part không hợp lệ")
        local_part = requested_local_part
        source = "manual"
    else:
        local_part = random_local_part()
        source = "generated"

    address = f"{local_part}@{settings.mail_domain}"
    mailbox = db.ensure_alias(address, source=source, label=label, expires_at=iso_in_hours(expires_in_hours))
    return {"item": mailbox}


@app.patch("/api/mailboxes/{alias_id}")
def update_mailbox(alias_id: int, payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    label = payload.get("label")
    status = payload.get("status")
    expires_in_hours = payload.get("expires_in_hours")
    expires_at = iso_in_hours(int(expires_in_hours)) if expires_in_hours else None
    mailbox = db.update_alias(alias_id, label=label, expires_at=expires_at, status=status)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox không tồn tại")
    return {"item": mailbox}


@app.post("/api/mailboxes/{alias_id}/expire")
def expire_mailbox(alias_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    mailbox = db.expire_alias(alias_id)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox không tồn tại")
    return {"item": mailbox}


@app.post("/api/mailboxes/{alias_id}/reactivate")
def reactivate_mailbox(alias_id: int, payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    hours = int(payload.get("expires_in_hours") or settings.default_alias_hours)
    mailbox = db.reactivate_alias(alias_id, hours)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox không tồn tại")
    return {"item": mailbox}


@app.delete("/api/mailboxes/{alias_id}")
def delete_mailbox(alias_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    mailbox = db.delete_alias(alias_id)
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Mailbox không tồn tại")
    return {"item": mailbox}


@app.get("/api/messages")
def list_messages(
    alias_id: int | None = Query(default=None),
    filter_name: str = Query(default="all"),
    search: str = Query(default=""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    return {"items": db.list_messages(alias_id=alias_id, filter_name=filter_name, search=search)}


@app.get("/api/messages/{message_id}")
def get_message(message_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")
    db.mark_message_read(message_id)
    return {"item": db.get_message(message_id)}


@app.delete("/api/messages/{message_id}")
def delete_message(message_id: int, _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.delete_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")
    return {"item": message}


@app.patch("/api/messages/{message_id}/important")
def set_message_important(message_id: int, payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.set_message_important(message_id, bool(payload.get("important")))
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")
    return {"item": message}


@app.post("/api/messages/{message_id}/translate")
def translate_email(message_id: int, payload: dict[str, Any] = Body(default={}), _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")

    try:
        result = translate_message(message, target_language=(payload.get("target_language") or DEFAULT_TARGET_LANGUAGE))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Dịch mail thất bại: {error}") from error

    return {"ok": True, "item": {"message_id": message_id, **result}}


@app.post("/api/messages/{message_id}/send")
def send_message(message_id: int, payload: dict[str, Any] = Body(...), _session=Depends(require_admin)) -> dict[str, Any]:
    message = db.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại")

    try:
        result = send_composed_message(
            source_message=message,
            mode=(payload.get("mode") or "reply").strip().lower(),
            to_value=payload.get("to", ""),
            cc_value=payload.get("cc", ""),
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Gửi mail thất bại: {error}") from error

    return {"ok": True, "item": result}


@app.post("/api/sync")
def trigger_sync(_session=Depends(require_admin)) -> dict[str, Any]:
    synced = mail_sync.sync_once()
    return {"ok": True, "synced": synced}


app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="static")
