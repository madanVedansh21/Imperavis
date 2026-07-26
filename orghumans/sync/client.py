"""OrgHumans Sync Client.

Connects to an OrgHumans Sync Server over TCP/JSON-lines, authenticates via HMAC challenge,
and streams state deltas.
"""

import asyncio
import logging
from typing import Callable, Optional

from orghumans.sync.protocol import (
    MSG_AUTH_CHALLENGE,
    MSG_AUTH_RESPONSE,
    MSG_AUTH_SUCCESS,
    MSG_SYNC_DELTA,
    compute_auth_response,
    decode_message,
    encode_message,
)
from orghumans.sync.server import PeerStream

logger = logging.getLogger(__name__)


class OrghumansSyncClient:
    def __init__(
        self,
        server_url: str,
        org_id: str,
        invite_key: str,
        username: str,
        on_delta_received: Optional[Callable[[dict], None]] = None,
    ):
        self.server_url = server_url
        self.org_id = org_id
        self.invite_key = invite_key
        self.username = username
        self.on_delta_received = on_delta_received
        self.stream: Optional[PeerStream] = None
        self.running = False

    async def connect_and_sync(self):
        self.running = True
        clean_url = self.server_url.replace("ws://", "").replace("tcp://", "").replace("http://", "")
        parts = clean_url.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 8765

        reader, writer = await asyncio.open_connection(host, port)
        self.stream = PeerStream(reader, writer)

        # 1. Challenge
        msg = await self.stream.recv_msg()
        if msg.get("type") != MSG_AUTH_CHALLENGE:
            raise ValueError("Expected auth_challenge from server")

        nonce = msg["payload"]["nonce"]
        resp_hmac = compute_auth_response(nonce, self.invite_key, self.username)

        # 2. Auth response
        await self.stream.send_msg(
            MSG_AUTH_RESPONSE,
            {
                "org_id": self.org_id,
                "username": self.username,
                "response": resp_hmac,
            },
        )

        # 3. Auth result
        res = await self.stream.recv_msg()
        if res.get("type") != MSG_AUTH_SUCCESS:
            raise ValueError(f"Auth failed: {res.get('payload')}")

        logger.info("Sync client connected and authenticated for org %s", self.org_id)

        # 4. Stream loop
        while self.running and not self.stream.closed:
            try:
                delta_msg = await asyncio.wait_for(self.stream.recv_msg(), timeout=0.5)
                if delta_msg.get("type") == MSG_SYNC_DELTA:
                    payload = delta_msg.get("payload")
                    if self.on_delta_received and payload:
                        self.on_delta_received(payload)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    async def send_delta(self, delta_payload: dict):
        if self.stream and self.running:
            await self.stream.send_msg(MSG_SYNC_DELTA, delta_payload)

    def stop(self):
        self.running = False
