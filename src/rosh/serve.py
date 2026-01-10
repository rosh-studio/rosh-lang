"""
Rosh Local World Server

A minimal WebSocket server for local testing of the REQUEST/CONFIRMED protocol.
This is a lightweight alternative to rosh.cloud for development and offline use.

Usage:
    rosh serve                    # Start on default port 8765
    rosh serve --port 9000       # Start on custom port

Protocol (Spec 0.3):
    - Clients send REQUEST_CREATE, REQUEST_MOVE, REQUEST_UPDATE, REQUEST_DELETE
    - Server validates and broadcasts CONFIRMED_* to ALL clients
    - Server assigns sequence numbers for ordering
    - Journal enables late-join sync
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict

try:
    import websockets
    import websockets.server
    HAS_WEBSOCKETS = True
except ImportError:
    websockets = None
    HAS_WEBSOCKETS = False


class LocalWorldManager:
    """Manage world state for local testing."""

    def __init__(self):
        self.worlds: Dict[str, dict] = {}  # world_id -> {objects, users, seq, journal}
        self.connections: Dict[str, Dict[str, any]] = {}  # world_id -> {user_id -> websocket}

    def _ensure_world(self, world_id: str):
        if world_id not in self.worlds:
            self.worlds[world_id] = {
                "objects": {},
                "users": {},
                "seq": 0,
                "journal": []
            }
        if world_id not in self.connections:
            self.connections[world_id] = {}

    def get_next_seq(self, world_id: str) -> int:
        self._ensure_world(world_id)
        self.worlds[world_id]["seq"] += 1
        return self.worlds[world_id]["seq"]

    def add_to_journal(self, world_id: str, entry: dict):
        self._ensure_world(world_id)
        self.worlds[world_id]["journal"].append(entry)

    def connect(self, world_id: str, websocket) -> str:
        self._ensure_world(world_id)
        user_id = str(uuid.uuid4())[:8]
        self.connections[world_id][user_id] = websocket
        self.worlds[world_id]["users"][user_id] = {
            "joined_at": datetime.now().isoformat()
        }
        return user_id

    def disconnect(self, world_id: str, user_id: str):
        if world_id in self.connections and user_id in self.connections[world_id]:
            del self.connections[world_id][user_id]
        if world_id in self.worlds and user_id in self.worlds[world_id]["users"]:
            del self.worlds[world_id]["users"][user_id]

    def get_state(self, world_id: str) -> dict:
        self._ensure_world(world_id)
        return self.worlds[world_id]

    def create_object(self, world_id: str, obj_id: str, obj_data: dict) -> bool:
        self._ensure_world(world_id)
        if obj_id in self.worlds[world_id]["objects"]:
            return False
        self.worlds[world_id]["objects"][obj_id] = obj_data
        return True

    def update_object(self, world_id: str, obj_id: str, updates: dict) -> bool:
        self._ensure_world(world_id)
        if obj_id not in self.worlds[world_id]["objects"]:
            return False
        self.worlds[world_id]["objects"][obj_id].update(updates)
        return True

    def delete_object(self, world_id: str, obj_id: str) -> bool:
        self._ensure_world(world_id)
        if obj_id not in self.worlds[world_id]["objects"]:
            return False
        del self.worlds[world_id]["objects"][obj_id]
        return True

    async def broadcast(self, world_id: str, message: dict, exclude_user: str = None):
        if world_id not in self.connections:
            return
        msg_text = json.dumps(message)
        for user_id, ws in list(self.connections[world_id].items()):
            if user_id != exclude_user:
                try:
                    await ws.send(msg_text)
                except:
                    pass

    async def send_to_user(self, world_id: str, user_id: str, message: dict):
        if world_id in self.connections and user_id in self.connections[world_id]:
            try:
                await self.connections[world_id][user_id].send(json.dumps(message))
            except:
                pass

    def get_user_count(self, world_id: str) -> int:
        return len(self.connections.get(world_id, {}))


# Global manager
manager = LocalWorldManager()


async def handle_client(websocket, path: str):
    """Handle a WebSocket client connection."""
    # Extract world_id from path (e.g., /world/myworld -> myworld)
    path_parts = path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == 'world':
        world_id = path_parts[1]
    elif len(path_parts) >= 3 and path_parts[1] == 'world':
        world_id = path_parts[2]
    else:
        world_id = 'default'

    user_id = manager.connect(world_id, websocket)
    print(f"[{world_id}] User {user_id} connected ({manager.get_user_count(world_id)} users)")

    try:
        # Send welcome
        state = manager.get_state(world_id)
        await websocket.send(json.dumps({
            "type": "CONNECTED",
            "world_id": world_id,
            "user_id": user_id,
            "user_count": manager.get_user_count(world_id),
            "state": state
        }))

        # Notify others
        await manager.broadcast(world_id, {
            "type": "USER_JOINED",
            "user_id": user_id,
            "user_count": manager.get_user_count(world_id)
        }, exclude_user=user_id)

        # Message loop
        async for message in websocket:
            try:
                data = json.loads(message)
                await handle_message(world_id, user_id, data)
            except json.JSONDecodeError:
                print(f"[{world_id}] Invalid JSON from {user_id}")

    except Exception:
        pass  # Connection closed
    finally:
        manager.disconnect(world_id, user_id)
        print(f"[{world_id}] User {user_id} disconnected ({manager.get_user_count(world_id)} users)")
        await manager.broadcast(world_id, {
            "type": "USER_LEFT",
            "user_id": user_id,
            "user_count": manager.get_user_count(world_id)
        })


async def handle_message(world_id: str, user_id: str, data: dict):
    """Handle incoming message from client."""
    msg_type = data.get("type", "")

    # ========================================
    # REQUEST/CONFIRMED Protocol (Spec 0.3)
    # ========================================

    if msg_type == "REQUEST_CREATE":
        request_id = data.get("request_id", str(uuid.uuid4()))
        obj_id = data.get("id") or f"obj_{uuid.uuid4().hex[:8]}"
        obj_data = {
            "type": data.get("object_type", "cube"),
            "x": data.get("x", 0),
            "y": data.get("y", 0),
            "z": data.get("z", 0),
            "color": data.get("color", "white"),
            "size": data.get("size", 1),
            "created_by": user_id,
            "cmd": data.get("cmd"),
            "object_type": data.get("object_type", "cube")
        }

        state = manager.get_state(world_id)
        if obj_id in state["objects"]:
            await manager.send_to_user(world_id, user_id, {
                "type": "REJECTED",
                "request_id": request_id,
                "reason": "duplicate_name",
                "message": f"Object '{obj_id}' already exists"
            })
        else:
            manager.create_object(world_id, obj_id, obj_data)
            seq = manager.get_next_seq(world_id)

            confirmed_msg = {
                "type": "CONFIRMED_CREATE",
                "request_id": request_id,
                "seq": seq,
                "id": obj_id,
                "uuid": str(uuid.uuid4()),
                "data": obj_data,
                "by": user_id
            }
            manager.add_to_journal(world_id, confirmed_msg)
            await manager.broadcast(world_id, confirmed_msg)

    elif msg_type == "REQUEST_MOVE":
        request_id = data.get("request_id", str(uuid.uuid4()))
        obj_id = data.get("id")

        if not obj_id:
            await manager.send_to_user(world_id, user_id, {
                "type": "REJECTED",
                "request_id": request_id,
                "reason": "missing_id",
                "message": "Object ID required"
            })
        else:
            state = manager.get_state(world_id)
            if obj_id not in state["objects"]:
                await manager.send_to_user(world_id, user_id, {
                    "type": "REJECTED",
                    "request_id": request_id,
                    "reason": "not_found",
                    "message": f"Object '{obj_id}' not found"
                })
            else:
                updates = {}
                if "x" in data: updates["x"] = data["x"]
                if "y" in data: updates["y"] = data["y"]
                if "z" in data: updates["z"] = data["z"]

                manager.update_object(world_id, obj_id, updates)
                seq = manager.get_next_seq(world_id)

                confirmed_msg = {
                    "type": "CONFIRMED_MOVE",
                    "request_id": request_id,
                    "seq": seq,
                    "id": obj_id,
                    "x": data.get("x"),
                    "y": data.get("y"),
                    "z": data.get("z"),
                    "by": user_id
                }
                manager.add_to_journal(world_id, confirmed_msg)
                await manager.broadcast(world_id, confirmed_msg)

    elif msg_type == "REQUEST_UPDATE":
        request_id = data.get("request_id", str(uuid.uuid4()))
        obj_id = data.get("id")

        if not obj_id:
            await manager.send_to_user(world_id, user_id, {
                "type": "REJECTED",
                "request_id": request_id,
                "reason": "missing_id",
                "message": "Object ID required"
            })
        else:
            state = manager.get_state(world_id)
            if obj_id not in state["objects"]:
                await manager.send_to_user(world_id, user_id, {
                    "type": "REJECTED",
                    "request_id": request_id,
                    "reason": "not_found",
                    "message": f"Object '{obj_id}' not found"
                })
            else:
                changes = {k: v for k, v in data.items() if k not in ("type", "id", "request_id")}
                manager.update_object(world_id, obj_id, changes)
                seq = manager.get_next_seq(world_id)

                confirmed_msg = {
                    "type": "CONFIRMED_UPDATE",
                    "request_id": request_id,
                    "seq": seq,
                    "id": obj_id,
                    "changes": changes,
                    "by": user_id
                }
                manager.add_to_journal(world_id, confirmed_msg)
                await manager.broadcast(world_id, confirmed_msg)

    elif msg_type == "REQUEST_DELETE":
        request_id = data.get("request_id", str(uuid.uuid4()))
        obj_id = data.get("id")

        if not obj_id:
            await manager.send_to_user(world_id, user_id, {
                "type": "REJECTED",
                "request_id": request_id,
                "reason": "missing_id",
                "message": "Object ID required"
            })
        else:
            state = manager.get_state(world_id)
            if obj_id not in state["objects"]:
                await manager.send_to_user(world_id, user_id, {
                    "type": "REJECTED",
                    "request_id": request_id,
                    "reason": "not_found",
                    "message": f"Object '{obj_id}' not found"
                })
            else:
                manager.delete_object(world_id, obj_id)
                seq = manager.get_next_seq(world_id)

                confirmed_msg = {
                    "type": "CONFIRMED_DELETE",
                    "request_id": request_id,
                    "seq": seq,
                    "id": obj_id,
                    "by": user_id
                }
                manager.add_to_journal(world_id, confirmed_msg)
                await manager.broadcast(world_id, confirmed_msg)

    # ========================================
    # Legacy Protocol (backwards compatibility)
    # ========================================

    elif msg_type == "CREATE":
        obj_id = data.get("id") or f"obj_{uuid.uuid4().hex[:8]}"
        obj_data = {
            "type": data.get("object_type", "cube"),
            "x": data.get("x", 0),
            "y": data.get("y", 0),
            "z": data.get("z", 0),
            "color": data.get("color", "white"),
            "size": data.get("size", 1),
            "created_by": user_id,
            "cmd": data.get("cmd"),
            "object_type": data.get("object_type", "cube")
        }
        if manager.create_object(world_id, obj_id, obj_data):
            await manager.broadcast(world_id, {
                "type": "OBJECT_CREATED",
                "id": obj_id,
                "data": obj_data,
                "by": user_id
            })

    elif msg_type == "MOVE":
        obj_id = data.get("id")
        if obj_id:
            updates = {}
            if "x" in data: updates["x"] = data["x"]
            if "y" in data: updates["y"] = data["y"]
            if "z" in data: updates["z"] = data["z"]
            if manager.update_object(world_id, obj_id, updates):
                await manager.broadcast(world_id, {
                    "type": "OBJECT_MOVED",
                    "id": obj_id,
                    "x": data.get("x"),
                    "y": data.get("y"),
                    "z": data.get("z"),
                    "by": user_id
                }, exclude_user=user_id)

    elif msg_type == "UPDATE":
        obj_id = data.get("id")
        if obj_id:
            changes = {k: v for k, v in data.items() if k not in ("type", "id")}
            if changes and manager.update_object(world_id, obj_id, changes):
                await manager.broadcast(world_id, {
                    "type": "OBJECT_UPDATED",
                    "id": obj_id,
                    "changes": changes,
                    "by": user_id
                }, exclude_user=user_id)

    elif msg_type == "DELETE":
        obj_id = data.get("id")
        if obj_id and manager.delete_object(world_id, obj_id):
            await manager.broadcast(world_id, {
                "type": "OBJECT_DELETED",
                "id": obj_id,
                "by": user_id
            })

    elif msg_type == "CHAT":
        await manager.broadcast(world_id, {
            "type": "CHAT",
            "by": user_id,
            "message": data.get("message", "")
        })

    elif msg_type == "PING":
        await manager.send_to_user(world_id, user_id, {"type": "PONG"})

    elif msg_type == "USERS":
        state = manager.get_state(world_id)
        users_list = []
        for uid in state["users"]:
            user_data = state["users"][uid]
            users_list.append({
                "id": uid,
                "joined_at": user_data.get("joined_at"),
                "is_you": uid == user_id
            })
        await manager.send_to_user(world_id, user_id, {
            "type": "USERS_LIST",
            "world_id": world_id,
            "users": users_list,
            "count": len(users_list)
        })


def run_server(port: int = 8765, host: str = "0.0.0.0"):
    """Run the local World Center server."""
    if not HAS_WEBSOCKETS:
        print("Error: websockets package not installed")
        print("Install with: pip install websockets")
        return 1

    # Import here to avoid issues when websockets not installed
    from websockets.server import serve as ws_serve

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║              Rosh Local World Center                      ║
║              Protocol: Spec 0.3                           ║
╠═══════════════════════════════════════════════════════════╣
║  WebSocket: ws://{host}:{port}/world/<world-name>
║                                                           ║
║  Connect in REPL:                                         ║
║    connect local                                          ║
║    # or                                                   ║
║    connect ws://localhost:{port}/world/myworld
╚═══════════════════════════════════════════════════════════╝
""")

    async def main():
        async with ws_serve(handle_client, host, port):
            await asyncio.Future()  # Run forever

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")
    return 0


if __name__ == "__main__":
    run_server()
