"""
Project Twin - WebSocket networking for shared worlds.

This module handles all WebSocket communication for syncing Rosh worlds
between multiple clients (terminals, browsers, etc.).
"""

import json
import threading
from typing import Optional, Callable, Dict, Any, List

# Default server URL
DEFAULT_SERVER = "wss://rosh.cloud/ws/world/"


class TwinConnection:
    """Manages a WebSocket connection to a Project Twin shared world."""

    def __init__(self, server_url: str = DEFAULT_SERVER):
        self.server_url = server_url
        self.ws = None
        self.user_id: Optional[str] = None
        self.world_id: Optional[str] = None
        self.world_state: Dict[str, Any] = {"objects": {}}
        self._message_queue: List[Dict] = []
        self._receiver_thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._on_message: Optional[Callable[[Dict], None]] = None

    @property
    def connected(self) -> bool:
        """Check if currently connected to a world."""
        return self.ws is not None

    def connect(self, world: str = "default") -> Dict[str, Any]:
        """
        Connect to a shared world.

        Args:
            world: The world ID to join (default: "default")

        Returns:
            Dict with connection info: user_id, user_count, state

        Raises:
            ImportError: If websocket-client package not installed
            Exception: If connection fails
        """
        if self.ws is not None:
            raise Exception(f"Already connected to '{self.world_id}'. Disconnect first.")

        try:
            import websocket
        except ImportError:
            raise ImportError("websocket-client package required. Install with: uv add websocket-client")

        uri = f"{self.server_url}{world}"
        self.ws = websocket.create_connection(uri)
        self.world_id = world

        # Receive initial CONNECTED message
        initial = json.loads(self.ws.recv())
        if initial['type'] == 'CONNECTED':
            self.user_id = initial['user_id']
            self.world_state.update(initial['state'])

            # Start background receiver thread
            self._stop_event = threading.Event()
            self._receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
            self._receiver_thread.start()

            return {
                "user_id": self.user_id,
                "world_id": self.world_id,
                "user_count": initial['user_count'],
                "state": initial['state']
            }
        else:
            self.ws.close()
            self.ws = None
            raise Exception(f"Unexpected response: {initial}")

    def disconnect(self):
        """Disconnect from the current world."""
        if self.ws is None:
            return

        try:
            if self._stop_event:
                self._stop_event.set()
            self.ws.close()
        except:
            pass
        finally:
            self.ws = None
            self.user_id = None
            self.world_id = None
            self.world_state = {"objects": {}}
            self._message_queue = []

    def _receiver_loop(self):
        """Background thread that receives messages from the server."""
        import websocket as ws_module
        while not self._stop_event.is_set():
            try:
                self.ws.settimeout(0.5)
                msg_str = self.ws.recv()
                msg = json.loads(msg_str)
                self._message_queue.append(msg)
                # Also call the callback if set
                if self._on_message:
                    self._on_message(msg)
            except ws_module.WebSocketTimeoutException:
                continue
            except Exception:
                break

    def get_pending_messages(self) -> List[Dict]:
        """Get and clear all pending messages from the queue."""
        messages = self._message_queue[:]
        self._message_queue = []
        return messages

    def on_message(self, callback: Callable[[Dict], None]):
        """Set a callback for incoming messages."""
        self._on_message = callback

    # === Outgoing messages ===

    def send_create(self, obj_id: str, obj_type: str, color: str = "green",
                    x: float = 0, y: float = 0, z: float = 0, size: float = 1):
        """Broadcast object creation to the world."""
        if not self.connected:
            return
        self.ws.send(json.dumps({
            "type": "CREATE",
            "id": obj_id,
            "object_type": obj_type,
            "color": color,
            "x": x, "y": y, "z": z,
            "size": size
        }))

    def send_delete(self, obj_id: str):
        """Broadcast object deletion to the world."""
        if not self.connected:
            return
        self.ws.send(json.dumps({
            "type": "DELETE",
            "id": obj_id
        }))

    def send_update(self, obj_id: str, **properties):
        """Broadcast property updates for an object."""
        if not self.connected:
            return
        self.ws.send(json.dumps({
            "type": "UPDATE",
            "id": obj_id,
            **properties
        }))

    def send_move(self, obj_id: str, x: float, y: float, z: float = 0):
        """Broadcast object position change."""
        if not self.connected:
            return
        self.ws.send(json.dumps({
            "type": "MOVE",
            "id": obj_id,
            "x": x, "y": y, "z": z
        }))

    def send_chat(self, message: str):
        """Send a chat message to the world."""
        if not self.connected:
            return
        self.ws.send(json.dumps({
            "type": "CHAT",
            "message": message
        }))

    def request_users(self):
        """Request list of connected users."""
        if not self.connected:
            return
        self.ws.send(json.dumps({"type": "USERS"}))

    def send_reset(self):
        """Request world reset (clears all objects)."""
        if not self.connected:
            return
        self.ws.send(json.dumps({"type": "RESET"}))

    # === Process incoming messages ===

    def process_message(self, msg: Dict) -> Optional[str]:
        """
        Process a message from the server and update local state.

        Returns a human-readable string describing the message, or None.
        """
        msg_type = msg.get('type')

        if msg_type == 'USER_JOINED':
            return f"[twin] {msg['user_id']} joined ({msg['user_count']} users)"

        elif msg_type == 'USER_LEFT':
            return f"[twin] {msg['user_id']} left ({msg['user_count']} users)"

        elif msg_type == 'OBJECT_CREATED':
            self.world_state['objects'][msg['id']] = msg['data']
            if msg.get('by') != self.user_id:
                return f"[twin] + {msg['id']}: {msg['data']['type']} by {msg['by']}"
            return None

        elif msg_type == 'OBJECT_DELETED':
            if msg['id'] in self.world_state['objects']:
                del self.world_state['objects'][msg['id']]
            if msg.get('by') != self.user_id:
                return f"[twin] - {msg['id']} deleted by {msg['by']}"
            return None

        elif msg_type == 'OBJECT_UPDATED':
            if msg['id'] in self.world_state['objects']:
                self.world_state['objects'][msg['id']].update(msg.get('changes', {}))
            if msg.get('by') != self.user_id:
                changes = msg.get('changes', {})
                return f"[twin] ~ {msg['id']} updated by {msg['by']}: {changes}"
            return None

        elif msg_type == 'OBJECT_MOVED':
            if msg['id'] in self.world_state['objects']:
                obj = self.world_state['objects'][msg['id']]
                obj['x'] = msg.get('x', obj.get('x', 0))
                obj['y'] = msg.get('y', obj.get('y', 0))
                obj['z'] = msg.get('z', obj.get('z', 0))
            if msg.get('by') != self.user_id:
                return f"[twin] ~ {msg['id']} moved to ({msg.get('x')}, {msg.get('y')}, {msg.get('z')})"
            return None

        elif msg_type == 'CHAT':
            sender = msg.get('by') or msg.get('user_id', '?')
            return f"[{sender}] {msg['message']}"

        elif msg_type == 'USERS_LIST':
            lines = [f"=== Users in '{msg['world_id']}' ({msg['count']}) ==="]
            for user in msg['users']:
                tag = " (you)" if user.get('is_you') else ""
                lines.append(f"  {user['id']}{tag}")
            return "\n".join(lines)

        elif msg_type == 'ERROR':
            return f"[twin error] {msg.get('message', 'Unknown error')}"

        elif msg_type == 'WORLD_RESET':
            self.world_state['objects'] = {}
            return f"[twin] World reset by {msg['by']} ({msg.get('deleted_count', 0)} objects cleared)"

        return None


# Global singleton for CLI use
_connection: Optional[TwinConnection] = None


def get_connection() -> TwinConnection:
    """Get or create the global TwinConnection instance."""
    global _connection
    if _connection is None:
        _connection = TwinConnection()
    return _connection
