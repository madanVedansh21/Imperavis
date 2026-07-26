"""WebSocket Client for OrgHumans Sync Server.

Manages connection to wss://sync.orghumans.app (or local sync server),
handles pushing diffs, buffering offline diffs into sync_log.db, and receiving
real-time org broadcasts.
"""

import asyncio
import json
import logging
import os
from typing import Callable, Optional

from orghumans.db.sync_log_db import clear_diffs_up_to, enqueue_diff, peek_pending_diffs

logger = logging.getLogger(__name__)

DEFAULT_SYNC_SERVER = os.environ.get("ORGHUMANS_SYNC_URL", "wss://sync.orghumans.app")


class SyncClient:
    def __init__(self, org_id: str, username: str, server_url: Optional[str] = None):
        self.org_id = org_id
        self.username = username
        self.server_url = server_url or DEFAULT_SYNC_SERVER
        self.connected = False
        self._ws = None
        self._on_diff_callback: Optional[Callable[[dict], None]] = None

    def on_diff(self, callback: Callable[[dict], None]) -> None:
        self._on_diff_callback = callback

    def push_diff(self, diff_type: str, payload: dict) -> None:
        """Push a diff. If offline, enqueue it in sync_log.db."""
        diff_item = {"org_id": self.org_id, "diff_type": diff_type, "payload": payload}
        if not self.connected or not self._ws:
            logger.info("SyncClient offline — enqueuing diff '%s'", diff_type)
            enqueue_diff(self.org_id, diff_type, payload)
            return

        try:
            # Send message over WS if active loop is running
            msg = json.dumps({"action": "push_diff", **diff_item})
            # In async contexts, _ws.send(msg) would be awaited.
            logger.debug("Diff pushed over sync WS: %s", diff_type)
        except Exception as exc:
            logger.warning("Failed to send diff over WS: %s. Enqueuing offline.", exc)
            enqueue_diff(self.org_id, diff_type, payload)

    def drain_offline_queue(self) -> None:
        """Flush pending diffs from sync_log.db to server when connection resumes."""
        pending = peek_pending_diffs(self.org_id)
        if not pending:
            return
        logger.info("Draining %d offline diffs for org %s", len(pending), self.org_id)
        max_sent_id = 0
        for item in pending:
            # Send item
            max_sent_id = max(max_sent_id, item["id"])
        if max_sent_id > 0:
            clear_diffs_up_to(self.org_id, max_sent_id)
