"""Tunnel management and MT webhook registration API routes.

Endpoints:
- POST /api/tunnel/start          Start ngrok tunnel
- POST /api/tunnel/stop           Stop ngrok tunnel
- GET  /api/tunnel/status         Poll tunnel health
- POST /api/tunnel/register-webhook  Auto-register webhook endpoint in MT
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse
from loguru import logger
from modern_treasury import AsyncModernTreasury

router = APIRouter()

WEBHOOK_PATH = "/webhooks/mt"


@router.post("/api/tunnel/start", include_in_schema=False)
async def tunnel_start(
    request: Request,
    authtoken: str = Form(...),
    domain: str = Form(""),
):
    """Start the ngrok tunnel.  Persists authtoken to runs/.tunnel_config.json."""
    mgr = request.app.state.tunnel
    try:
        url = mgr.start(
            authtoken=authtoken.strip(),
            domain=domain.strip() or None,
        )
        return {"ok": True, "url": url}
    except Exception as exc:
        logger.warning("Tunnel start failed: {}", exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/api/tunnel/stop", include_in_schema=False)
async def tunnel_stop(request: Request):
    """Stop the ngrok tunnel."""
    mgr = request.app.state.tunnel
    mgr.stop()
    return {"ok": True}


@router.get("/api/tunnel/status", include_in_schema=False)
async def tunnel_status(request: Request):
    """Return current tunnel connectivity and URL."""
    mgr = request.app.state.tunnel
    status = mgr.get_status()
    status["webhook_endpoint_id"] = mgr.saved_webhook_endpoint_id
    status["has_authtoken"] = bool(
        request.app.state.settings.ngrok_authtoken or mgr.saved_authtoken
    )
    return status


@router.post("/api/tunnel/register-webhook", include_in_schema=False)
async def register_webhook(
    request: Request,
    api_key: str = Form(...),
    org_id: str = Form(...),
):
    """Create or update a webhook endpoint in MT pointing to the tunnel URL.

    Finds existing endpoints whose URL contains ``/webhooks/mt`` and
    updates them if the tunnel URL has changed; otherwise creates a new
    endpoint.  Captures the ``webhook_key`` (signing secret) on creation
    and auto-applies it for signature verification.
    """
    mgr = request.app.state.tunnel
    status = mgr.get_status()
    if not status.get("connected") or not status.get("url"):
        return JSONResponse(
            {"ok": False, "error": "No active tunnel. Start the tunnel first."},
            status_code=400,
        )

    tunnel_url = status["url"]
    full_webhook_url = tunnel_url.rstrip("/") + WEBHOOK_PATH

    try:
        async with AsyncModernTreasury(
            api_key=api_key, organization_id=org_id
        ) as client:
            existing = None
            async for ep in client.webhook_endpoints.list():
                if WEBHOOK_PATH in (ep.url or ""):
                    existing = ep
                    break

            if existing:
                if existing.url == full_webhook_url:
                    return {
                        "ok": True,
                        "action": "already_registered",
                        "endpoint_id": existing.id,
                        "url": existing.url,
                    }
                await client.webhook_endpoints.update(
                    existing.id, url=full_webhook_url
                )
                logger.info(
                    "Updated MT webhook endpoint {} -> {}",
                    existing.id,
                    full_webhook_url,
                )
                return {
                    "ok": True,
                    "action": "updated",
                    "endpoint_id": existing.id,
                    "url": full_webhook_url,
                }

            created = await client.webhook_endpoints.create(
                url=full_webhook_url
            )
            webhook_key = getattr(created, "webhook_key", "") or ""
            mgr.save_webhook_endpoint(created.id, webhook_key)

            if webhook_key:
                request.app.state.settings.webhook_secret = webhook_key
                logger.info(
                    "Created MT webhook endpoint {}; signing secret auto-configured",
                    created.id,
                )
            else:
                logger.info("Created MT webhook endpoint {}", created.id)

            return {
                "ok": True,
                "action": "created",
                "endpoint_id": created.id,
                "url": full_webhook_url,
                "webhook_key_captured": bool(webhook_key),
            }

    except Exception as exc:
        logger.warning("Webhook registration failed: {}", exc)
        return JSONResponse(
            {"ok": False, "error": str(exc)}, status_code=500
        )
