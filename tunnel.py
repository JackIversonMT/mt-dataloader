"""Ngrok tunnel lifecycle management.

Provides :class:`TunnelManager` which wraps *pyngrok* to start/stop an
ngrok tunnel and persists config (authtoken, domain, webhook endpoint ID)
to ``runs/.tunnel_config.json`` so that settings survive Docker container
restarts via the volume mount.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from loguru import logger

_CONFIG_FILENAME = ".tunnel_config.json"


class TunnelManager:
    """Manages ngrok tunnel lifecycle and persistent config.

    Settings priority: env-var override > persisted config > empty.
    """

    def __init__(self, runs_dir: str = "runs") -> None:
        self._config_path = Path(runs_dir) / _CONFIG_FILENAME
        self._active_url: str | None = None
        self._config: dict = self._load_config()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        if self._config_path.exists():
            try:
                return json.loads(self._config_path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not load tunnel config: {}", exc)
        return {}

    def _save_config(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(self._config, indent=2), "utf-8"
        )

    # ------------------------------------------------------------------
    # Tunnel lifecycle
    # ------------------------------------------------------------------

    def start(
        self,
        authtoken: str,
        port: int = 8000,
        domain: str | None = None,
    ) -> str:
        """Start an ngrok tunnel.  Returns the public HTTPS URL."""
        from pyngrok import conf, ngrok

        conf.get_default().auth_token = authtoken
        kwargs: dict = {"addr": str(port), "proto": "http"}
        if domain:
            kwargs["hostname"] = domain

        tunnel = ngrok.connect(**kwargs)
        self._active_url = tunnel.public_url
        logger.info("Tunnel started: {}", self._active_url)

        self._config["authtoken"] = authtoken
        if domain:
            self._config["domain"] = domain
        self._save_config()

        return self._active_url

    def stop(self) -> None:
        """Disconnect all tunnels."""
        try:
            from pyngrok import ngrok

            ngrok.disconnect_all()
            ngrok.kill()
        except Exception as exc:
            logger.debug("Tunnel stop: {}", exc)
        self._active_url = None
        logger.info("Tunnel stopped")

    def get_status(self) -> dict:
        """Return ``{connected, url}`` by checking pyngrok then the local agent API."""
        try:
            from pyngrok import ngrok

            tunnels = ngrok.get_tunnels()
            for t in tunnels:
                if t.public_url.startswith("https://"):
                    return {"connected": True, "url": t.public_url}
        except Exception:
            pass

        return _probe_external_ngrok()

    # ------------------------------------------------------------------
    # Saved properties
    # ------------------------------------------------------------------

    @property
    def saved_authtoken(self) -> str:
        return self._config.get("authtoken", "")

    @property
    def saved_domain(self) -> str:
        return self._config.get("domain", "")

    @property
    def saved_webhook_endpoint_id(self) -> str:
        return self._config.get("webhook_endpoint_id", "")

    @property
    def saved_webhook_key(self) -> str:
        return self._config.get("webhook_key", "")

    def save_webhook_endpoint(self, endpoint_id: str, webhook_key: str) -> None:
        self._config["webhook_endpoint_id"] = endpoint_id
        self._config["webhook_key"] = webhook_key
        self._save_config()


def _probe_external_ngrok() -> dict:
    """Probe the ngrok local agent API (for externally-run ngrok)."""
    try:
        with httpx.Client(timeout=2.0) as http:
            resp = http.get("http://127.0.0.1:4040/api/tunnels")
            if resp.status_code == 200:
                data = resp.json()
                for tunnel in data.get("tunnels", []):
                    url = tunnel.get("public_url", "")
                    if url.startswith("https://"):
                        return {"connected": True, "url": url}
    except Exception:
        pass
    return {"connected": False, "url": None}
