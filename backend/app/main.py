from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .auth import clear_session, create_session, require_admin, require_session, require_user
from .config import settings
from .events import inbox_events
from .imap_sync import MailSyncService
from .mailer import send_composed_message
from .translator import DEFAULT_TARGET_LANGUAGE, translate_message
from .utils import iso_in_hours, is_valid_local_part, normalize_lookup_address, random_local_part


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


def _format_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _admin_event_stream(request: Request):
    last_version = inbox_events.get_global_version()
    yield _format_sse("ready", {"version": last_version, "mail_sync": mail_sync.get_status()})
    while True:
        if await request.is_disconnected():
            break
        next_version = await asyncio.to_thread(inbox_events.wait_for_global, last_version, 25.0)
        if await request.is_disconnected():
            break
        if next_version == last_version:
            yield _format_sse("heartbeat", {"version": last_version, "mail_sync": mail_sync.get_status()})
            continue
        last_version = next_version
        yield _format_sse("messages", {"version": last_version, "mail_sync": mail_sync.get_status()})


async def _user_event_stream(request: Request, alias: str):
    last_version = inbox_events.get_alias_version(alias)
    yield _format_sse("ready", {"version": last_version, "alias": alias, "mail_sync": mail_sync.get_status()})
    while True:
        if await request.is_disconnected():
            break
        next_version = await asyncio.to_thread(inbox_events.wait_for_alias, alias, last_version, 25.0)
        if await request.is_disconnected():
            break
        if next_version == last_version:
            yield _format_sse("heartbeat", {"version": last_version, "alias": alias, "mail_sync": mail_sync.get_status()})
            continue
        last_version = next_version
        yield _format_sse("messages", {"version": last_version, "alias": alias, "mail_sync": mail_sync.get_status()})


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path in {"/", "/index.html", "/user.html", "/app.js", "/user.js", "/style.css", "/user.css"}:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "mail_domain": settings.mail_domain, "public_domain": settings.public_domain}


@app.get("/api/mail-sync/status")
def mail_sync_status(_session=Depends(require_session)) -> dict[str, Any]:
    return {"ok": True, "item": mail_sync.get_status()}


@app.get("/api/events")
async def stream_admin_events(request: Request, _session=Depends(require_admin)):
    return StreamingResponse(
        _admin_event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/auth/login")
def login(response: Response, payload: dict[str, str] = Body(...)) -> dict[str, Any]:
    username = (payload.get("username") or payload.get("email") or "").strip()
    password = payload.get("password", "")
    if username == settings.admin_username and password == settings.admin_password:
        session = create_session(response, settings.admin_username, "admin")
    elif username == settings.user_username and password == settings.user_password:
        session = create_session(response, settings.user_username, "user")
    else:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")
    return {
        "ok": True,
        "user": {"username": session["username"], "role": session["role"]},
        "expires_at": session["expires_at"],
    }


@app.post("/api/auth/logout")
def logout(response: Response, session=Depends(require_session)) -> dict[str, bool]:
    clear_session(response, session["token"])
    return {"ok": True}


@app.get("/api/auth/session")
def session(session=Depends(require_session)) -> dict[str, Any]:
    return {"ok": True, "user": {"username": session["username"], "role": session["role"]}, "expires_at": session["expires_at"]}


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


@app.get("/api/debug/message-timings")
def list_debug_message_timings(
    limit: int = Query(default=20, ge=1, le=100),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    return {"items": db.list_recent_message_timings(limit=limit)}


@app.delete("/api/messages")
def delete_messages_in_scope(
    alias_id: int | None = Query(default=None),
    filter_name: str = Query(default="all"),
    search: str = Query(default=""),
    _session=Depends(require_admin),
) -> dict[str, Any]:
    result = db.delete_messages_by_scope(alias_id=alias_id, filter_name=filter_name, search=search)
    if result["deleted_count"]:
        inbox_events.publish(result["recipient_addresses"])
    return {"ok": True, "deleted_count": result["deleted_count"]}


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
    inbox_events.publish([message["recipient_address"]])
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


@app.get("/api/public/inbox")
def public_list_inbox(alias: str = Query(...), _session=Depends(require_user)) -> dict[str, Any]:
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    items = db.list_public_messages(recipient_address=address)
    return {"ok": True, "alias": {"address": address, "message_count": len(items)}, "items": items}


@app.get("/api/public/events")
async def stream_user_events(
    request: Request,
    alias: str = Query(...),
    _session=Depends(require_user),
):
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return StreamingResponse(
        _user_event_stream(request, address),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/public/sync")
def public_trigger_sync(_session=Depends(require_user)) -> dict[str, Any]:
    synced = mail_sync.sync_once()
    return {"ok": True, "synced": synced}


@app.get("/api/public/messages/{message_id}")
def public_get_message(message_id: int, alias: str = Query(...), _session=Depends(require_user)) -> dict[str, Any]:
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    message = db.get_message_for_address(message_id, address)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại cho alias này")

    db.mark_message_read(message_id)
    return {"ok": True, "item": db.get_message_for_address(message_id, address)}


@app.post("/api/public/messages/{message_id}/translate")
def public_translate_email(
    message_id: int,
    alias: str = Query(...),
    payload: dict[str, Any] = Body(default={}),
    _session=Depends(require_user),
) -> dict[str, Any]:
    try:
        address = normalize_lookup_address(alias, settings.mail_domain)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    message = db.get_message_for_address(message_id, address)
    if message is None:
        raise HTTPException(status_code=404, detail="Email không tồn tại cho alias này")

    try:
        result = translate_message(message, target_language=(payload.get("target_language") or DEFAULT_TARGET_LANGUAGE))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Dịch mail thất bại: {error}") from error

    return {"ok": True, "item": {"message_id": message_id, **result}}


@app.post("/api/sync")
def trigger_sync(_session=Depends(require_admin)) -> dict[str, Any]:
    synced = mail_sync.sync_once()
    return {"ok": True, "synced": synced}


app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="static")
