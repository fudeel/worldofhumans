# game/network/ws_server.py
"""
Async WebSocket server for the game client frontend.

Accepts WebSocket connections, delegates message handling to the
``WSBridge``, and runs a periodic world-state broadcast loop.

This module is a standalone entry point.  It boots the same game
infrastructure as ``game.main`` but exposes it over WebSockets
instead of a terminal prompt.  Removing this file and its
siblings (``ws_protocol.py``, ``ws_bridge.py``) has no effect
on the rest of the codebase.
"""

from __future__ import annotations

import asyncio
import json
import logging

try:
    import websockets
    from websockets.asyncio.server import serve, ServerConnection
except ImportError:
    raise ImportError(
        "The 'websockets' package is required for the WebSocket server. "
        "Install it with: pip install websockets"
    )

from game.network.ws_bridge import WSBridge, WSClient
from game.network.ws_protocol import WSMessageType, decode_message, encode_message

logger = logging.getLogger(__name__)

# Interval between full world-state broadcasts (seconds).
_WORLD_STATE_INTERVAL = 0.1


class WSServer:
    """
    WebSocket server wrapping the game bridge.

    Parameters
    ----------
    bridge:
        The ``WSBridge`` that connects WebSocket clients to the
        game engine.
    host:
        Bind address for the server.
    port:
        Bind port for the server.
    """

    def __init__(
        self, bridge: WSBridge, host: str = "0.0.0.0", port: int = 8765
    ) -> None:
        self._bridge = bridge
        self._host = host
        self._port = port

    async def start(self) -> None:
        """Start the WebSocket server and world-state broadcast loop."""
        loop = asyncio.get_running_loop()
        self._bridge.set_event_loop(loop)

        broadcast_task = asyncio.create_task(self._broadcast_loop())

        logger.info("WebSocket server starting on ws://%s:%d", self._host, self._port)
        async with serve(self._handle_client, self._host, self._port) as server:
            logger.info("WebSocket server listening on ws://%s:%d", self._host, self._port)
            await asyncio.Future()  # run forever

    async def _handle_client(self, websocket: ServerConnection) -> None:
        """Handle a single WebSocket client connection."""
        client = WSClient(websocket)
        self._bridge.register_client(client)
        logger.info("Client connected: %s", client.player_id)

        try:
            async for raw_message in websocket:
                await self._process_message(client, str(raw_message))
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected: %s", client.player_id)
        finally:
            self._bridge.unregister_client(client.player_id)
            logger.info("Client cleaned up: %s", client.player_id)

    async def _process_message(self, client: WSClient, raw: str) -> None:
        """Decode and route a single inbound WebSocket message."""
        try:
            msg_type, payload = decode_message(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            await client.ws.send(encode_message(
                WSMessageType.S_ERROR, {"message": f"Bad message: {exc}"}
            ))
            return

        if msg_type == WSMessageType.C_GET_CLASS_DATA:
            response = self._bridge.get_class_data()
            await client.ws.send(response)

        elif msg_type == WSMessageType.C_CREATE_CHARACTER:
            response = self._bridge.create_character(
                client,
                name=payload.get("name", "Unnamed"),
                race_str=payload.get("race", ""),
                class_str=payload.get("class_type", ""),
            )
            await client.ws.send(response)

        elif msg_type == WSMessageType.C_MOVE:
            self._bridge.handle_move(
                client,
                x=float(payload.get("x", 0)),
                y=float(payload.get("y", 0)),
            )

        elif msg_type == WSMessageType.C_ATTACK:
            self._bridge.handle_attack(
                client,
                target_id=payload.get("target_id", ""),
            )

        elif msg_type == WSMessageType.C_INTERACT:
            response = self._bridge.handle_interact(
                client,
                object_id=payload.get("object_id", ""),
            )
            await client.ws.send(response)

        elif msg_type == WSMessageType.C_DISCONNECT:
            self._bridge.unregister_client(client.player_id)

        else:
            await client.ws.send(encode_message(
                WSMessageType.S_ERROR,
                {"message": f"Unknown message type: {msg_type.value}"},
            ))

    async def _broadcast_loop(self) -> None:
        """Periodically send world-state snapshots to all clients."""
        while True:
            await asyncio.sleep(_WORLD_STATE_INTERVAL)
            clients = list(self._bridge._clients.values())
            for client in clients:
                if client.character is None:
                    continue
                state_msg = self._bridge.build_world_state(client)
                if state_msg:
                    try:
                        await client.ws.send(state_msg)
                    except Exception:
                        pass