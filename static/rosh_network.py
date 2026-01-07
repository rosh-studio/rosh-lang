"""
Rosh Network Module - Project Twin Multiplayer (Python)

Provides shared world functionality for Pygame and other Python targets.
Mirrors the JavaScript RoshNetwork module for cross-platform compatibility.

Usage:
    from rosh_network import RoshNetwork

    network = RoshNetwork(
        on_object_created=lambda id, data: create_object(id, data),
        on_object_deleted=lambda id: delete_object(id),
        on_log=lambda msg, style: print(msg)
    )
    network.connect('myworld')
    network.broadcast_create('cube1', {'type': 'cube', 'x': 0, 'y': 0, 'color': 'red'})
"""

import json
import threading
import time

# Try to import websocket-client, fall back gracefully
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("[RoshNetwork] websocket-client not installed. Run: pip install websocket-client")


class RoshNetwork:
    """WebSocket client for Rosh shared worlds."""

    DEFAULT_SERVER = 'wss://rosh.cloud/ws/world/'

    def __init__(self, on_object_created=None, on_object_deleted=None,
                 on_object_moved=None, on_chat=None, on_log=None, server_url=None):
        """
        Initialize the network client.

        Args:
            on_object_created: Callback(id, data) when remote user creates object
            on_object_deleted: Callback(id) when remote user deletes object
            on_object_moved: Callback(id, x, y, z) when remote user moves object
            on_chat: Callback(user_id, message) for chat messages
            on_log: Callback(message, style) for logging
            server_url: Custom WebSocket server URL
        """
        self.server_url = server_url or self.DEFAULT_SERVER
        self.ws = None
        self.user_id = None
        self.world_id = None
        self._thread = None
        self._running = False

        # Callbacks
        self.on_object_created = on_object_created
        self.on_object_deleted = on_object_deleted
        self.on_object_moved = on_object_moved
        self.on_chat = on_chat
        self.on_log = on_log or (lambda msg, style=None: print(f"[Network] {msg}"))

        # Message queue for thread-safe handling
        self._message_queue = []
        self._queue_lock = threading.Lock()

    def is_connected(self):
        """Check if connected to a shared world."""
        return self.ws is not None and self.ws.sock is not None and self.ws.sock.connected

    def connect(self, world='default'):
        """
        Connect to a shared world.

        Args:
            world: World name/ID (default: 'default')
        """
        if not WEBSOCKET_AVAILABLE:
            self.on_log("WebSocket not available. Install: pip install websocket-client", 'err')
            return False

        if self.is_connected():
            self.on_log(f"Already connected to world: {self.world_id}", 'warn')
            return False

        self.on_log(f"Connecting to shared world: {world}...", 'cyan')

        try:
            url = self.server_url + world
            self.ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            self.world_id = world

            # Run WebSocket in background thread
            self._running = True
            self._thread = threading.Thread(target=self._run_forever, daemon=True)
            self._thread.start()

            return True
        except Exception as e:
            self.on_log(f"Failed to connect: {e}", 'err')
            return False

    def disconnect(self):
        """Disconnect from current shared world."""
        if self.ws:
            self._running = False
            self.ws.close()
            self.on_log(f"Disconnected from shared world: {self.world_id}", 'ok')
            self.ws = None
            self.user_id = None
            self.world_id = None
            return True
        else:
            self.on_log("Not connected to any shared world", 'dim')
            return False

    def say(self, message):
        """Send a chat message."""
        if not self.is_connected():
            self.on_log('Not connected. Use "connect" first.', 'err')
            return False
        if not message:
            self.on_log('Usage: say <message>', 'dim')
            return False
        self._send({'type': 'CHAT', 'message': message})
        self.on_log(f'[you]: {message}', 'ok')
        return True

    def broadcast_create(self, id, data):
        """
        Broadcast object creation to connected clients.

        Args:
            id: Object ID/name
            data: Dict with type, x, y, z, color, size
        """
        if not self.is_connected():
            return False
        msg = {
            'type': 'CREATE',
            'id': id,
            'object_type': data.get('type', 'cube'),
            'x': data.get('x', 0),
            'y': data.get('y', 0),
            'z': data.get('z', 0),
            'color': data.get('color'),
            'size': data.get('size')
        }
        self._send(msg)
        return True

    def broadcast_delete(self, id):
        """Broadcast object deletion to connected clients."""
        if not self.is_connected():
            return False
        self._send({'type': 'DELETE', 'id': id})
        return True

    def broadcast_move(self, id, x, y, z=0):
        """Broadcast object move to connected clients."""
        if not self.is_connected():
            return False
        self._send({'type': 'MOVE', 'id': id, 'x': x, 'y': y, 'z': z})
        return True

    def list_users(self):
        """Request list of users in current world."""
        if not self.is_connected():
            self.on_log('Not connected. Use "connect" first.', 'err')
            return False
        self._send({'type': 'USERS'})
        return True

    def process_messages(self):
        """
        Process queued messages from the network thread.
        Call this from your game loop to handle network events safely.
        """
        with self._queue_lock:
            messages = self._message_queue[:]
            self._message_queue.clear()

        for msg in messages:
            self._handle_message(msg)

    # --- Private methods ---

    def _send(self, msg):
        """Send a JSON message."""
        if self.ws and self.is_connected():
            self.ws.send(json.dumps(msg))

    def _run_forever(self):
        """Run WebSocket event loop in background thread."""
        while self._running:
            try:
                self.ws.run_forever()
            except Exception as e:
                if self._running:
                    self.on_log(f"Connection error: {e}", 'err')
            time.sleep(1)  # Reconnect delay

    def _on_open(self, ws):
        """WebSocket connected."""
        self.on_log("WebSocket connected", 'dim')

    def _on_message(self, ws, message):
        """Queue incoming message for processing in main thread."""
        try:
            msg = json.loads(message)
            with self._queue_lock:
                self._message_queue.append(msg)
        except Exception as e:
            print(f"[RoshNetwork] Message parse error: {e}")

    def _on_error(self, ws, error):
        """WebSocket error."""
        self.on_log(f"Connection error: {error}", 'err')

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket closed."""
        if self._running:
            self.on_log("Disconnected from shared world", 'warn')

    def _handle_message(self, msg):
        """Handle a parsed message from the server."""
        msg_type = msg.get('type')

        if msg_type == 'CONNECTED':
            self.user_id = msg.get('user_id')
            self.on_log(f'Connected to "{self.world_id}" as user {self.user_id}', 'ok')
            self.on_log('Objects you create will be shared with others!', 'cyan')

        elif msg_type == 'OBJECT_CREATED':
            if msg.get('by') != self.user_id:
                data = msg.get('data', {})
                if self.on_object_created:
                    self.on_object_created(msg.get('id'), data)
                self.on_log(f"[{msg.get('by')}] created {msg.get('id')}", 'cyan')

        elif msg_type == 'OBJECT_DELETED':
            if msg.get('by') != self.user_id:
                if self.on_object_deleted:
                    self.on_object_deleted(msg.get('id'))
                self.on_log(f"[{msg.get('by')}] deleted {msg.get('id')}", 'cyan')

        elif msg_type == 'OBJECT_MOVED':
            if msg.get('by') != self.user_id:
                if self.on_object_moved:
                    self.on_object_moved(msg.get('id'), msg.get('x'), msg.get('y'), msg.get('z', 0))

        elif msg_type == 'CHAT':
            self.on_log(f"[{msg.get('by')}]: {msg.get('message')}", 'cyan')
            if self.on_chat:
                self.on_chat(msg.get('by'), msg.get('message'))

        elif msg_type == 'WORLD_STATE':
            objects = msg.get('objects', {})
            count = len(objects)
            if count > 0:
                self.on_log(f'Loading {count} shared object(s)...', 'dim')
                for obj_id, data in objects.items():
                    if self.on_object_created:
                        self.on_object_created(obj_id, data)

        elif msg_type == 'USERS_LIST':
            self.on_log(f"=== Users in \"{msg.get('world_id')}\" ({msg.get('count')}) ===", 'cyan')
            for user in msg.get('users', []):
                you_tag = ' (you)' if user.get('is_you') else ''
                style = 'ok' if user.get('is_you') else 'dim'
                self.on_log(f"  {user.get('id')}{you_tag}", style)

        elif msg_type == 'USER_JOINED':
            self.on_log(f"[{msg.get('user_id')}] joined ({msg.get('user_count')} users)", 'cyan')

        elif msg_type == 'USER_LEFT':
            self.on_log(f"[{msg.get('user_id')}] left ({msg.get('user_count')} users)", 'dim')


# Singleton instance for simple usage
_network = None

def get_network():
    """Get or create the global network instance."""
    global _network
    if _network is None:
        _network = RoshNetwork()
    return _network
