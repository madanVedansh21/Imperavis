"""OrgHumans Local-First Peer & Cross-Device Sync Server.

Listens for incoming peer connections over TCP/JSON-lines, performs HMAC-SHA256
authentication via invite key, maintains active connection pools per organisation,
and broadcasts incoming state deltas to peers in real time.
"""

import asyncio
import logging
from typing import Dict, Set

from orghumans.sync.protocol import (
    MSG_AUTH_CHALLENGE,
    MSG_AUTH_FAILED,
    MSG_AUTH_RESPONSE,
    MSG_AUTH_SUCCESS,
    MSG_PING,
    MSG_PONG,
    MSG_SYNC_DELTA,
    decode_message,
    encode_message,
    generate_challenge,
    verify_auth_response,
)

logger = logging.getLogger(__name__)


class PeerStream:
    """JSON-line transport over asyncio reader/writer."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.closed = False

    async def send_msg(self, msg_type: str, payload: dict):
        if self.closed:
            return
        line = encode_message(msg_type, payload) + "\n"
        self.writer.write(line.encode("utf-8"))
        await self.writer.drain()

    async def recv_msg(self) -> dict:
        line = await self.reader.readline()
        if not line:
            self.closed = True
            raise asyncio.IncompleteReadError(b"", 0)
        return decode_message(line.decode("utf-8").strip())

    async def close(self):
        self.closed = True
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass


class OrgConnection:
    def __init__(self, stream: PeerStream, org_id: str, username: str):
        self.stream = stream
        self.org_id = org_id
        self.username = username


class OrghumansSyncServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, invite_keys: Dict[str, str] = None):
        self.host = host
        self.port = port
        self.invite_keys = invite_keys or {}
        self.connections: Dict[str, Set[OrgConnection]] = {}
        self.server = None

    def register_org(self, org_id: str, invite_key: str):
        self.invite_keys[org_id] = invite_key

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        stream = PeerStream(reader, writer)
        nonce = generate_challenge()

        try:
            # 1. Challenge
            await stream.send_msg(MSG_AUTH_CHALLENGE, {"nonce": nonce})

            # 2. Auth response
            msg = await asyncio.wait_for(stream.recv_msg(), timeout=10.0)
            if msg.get("type") != MSG_AUTH_RESPONSE:
                await stream.send_msg(MSG_AUTH_FAILED, {"reason": "Expected auth_response"})
                await stream.close()
                return

            payload = msg.get("payload", {})
            org_id = payload.get("org_id")
            username = payload.get("username")
            response_hmac = payload.get("response")

            invite_key = self.invite_keys.get(org_id)
            if not invite_key or not verify_auth_response(nonce, invite_key, username, response_hmac):
                await stream.send_msg(MSG_AUTH_FAILED, {"reason": "HMAC authentication failed"})
                await stream.close()
                return

            # Auth Success
            conn = OrgConnection(stream, org_id, username)
            if org_id not in self.connections:
                self.connections[org_id] = set()
            self.connections[org_id].add(conn)

            await stream.send_msg(MSG_AUTH_SUCCESS, {"org_id": org_id, "username": username})
            logger.info("Sync peer @%s authenticated for org %s", username, org_id)

            # 3. Message loop
            while not stream.closed:
                client_msg = await stream.recv_msg()
                msg_type = client_msg.get("type")

                if msg_type == MSG_PING:
                    await stream.send_msg(MSG_PONG, {})
                elif msg_type == MSG_SYNC_DELTA:
                    await self._broadcast_delta(org_id, conn, client_msg.get("payload"))

        except Exception:
            pass
        finally:
            self._disconnect(stream)

    async def _broadcast_delta(self, org_id: str, sender: OrgConnection, delta_payload: dict):
        peers = self.connections.get(org_id, set())
        for peer in list(peers):
            if peer != sender:
                try:
                    await peer.stream.send_msg(MSG_SYNC_DELTA, delta_payload)
                except Exception:
                    pass

    def _disconnect(self, stream: PeerStream):
        for org_id, conn_set in list(self.connections.items()):
            to_remove = [c for c in conn_set if c.stream == stream]
            for c in to_remove:
                conn_set.remove(c)

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
