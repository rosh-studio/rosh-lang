/**
 * Rosh Network Module - Project Twin Multiplayer
 *
 * Provides shared world functionality for any Rosh target (Three.js, Phaser, etc.)
 *
 * Usage:
 *   const network = RoshNetwork.init({ adapter, log, serverUrl });
 *   network.connect('worldName');
 *   network.say('hello');
 *   network.disconnect();
 */

const RoshNetwork = (function() {
  'use strict';

  // Default server URL
  const DEFAULT_SERVER = 'wss://rosh.cloud/ws/world/';

  // Module state
  let socket = null;
  let userId = null;
  let worldId = null;
  let serverUrl = DEFAULT_SERVER;
  let adapter = null;
  let log = console.log;

  /**
   * Initialize the network module
   * @param {Object} options
   * @param {Object} options.adapter - Object with createObject, deleteObject, moveObject methods
   * @param {Function} options.log - Logging function (message, style)
   * @param {string} options.serverUrl - WebSocket server URL (optional)
   */
  function init(options = {}) {
    adapter = options.adapter || {};
    log = options.log || console.log;
    serverUrl = options.serverUrl || DEFAULT_SERVER;
    return RoshNetwork;
  }

  /**
   * Check if connected to a shared world
   */
  function isConnected() {
    return socket && socket.readyState === WebSocket.OPEN;
  }

  /**
   * Get current connection info
   */
  function getConnectionInfo() {
    return {
      connected: isConnected(),
      worldId: worldId,
      userId: userId
    };
  }

  /**
   * Connect to a shared world
   * @param {string} world - World name/ID (default: 'default')
   */
  function connect(world = 'default') {
    if (isConnected()) {
      log('Already connected to world: ' + worldId, 'warn');
      log('Use "disconnect" first to leave current world', 'dim');
      return false;
    }

    log('Connecting to shared world: ' + world + '...', 'cyan');

    try {
      socket = new WebSocket(serverUrl + world);
      worldId = world;

      socket.onopen = () => {
        log('WebSocket connected', 'dim');
      };

      socket.onerror = (e) => {
        log('Connection failed - server may be offline', 'err');
        log('You can still work offline. Use "save" to keep your work.', 'dim');
      };

      socket.onclose = () => {
        log('Disconnected from shared world', 'warn');
        socket = null;
        userId = null;
        worldId = null;
      };

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleMessage(msg);
        } catch (e) {
          console.error('Twin message error:', e);
        }
      };

      return true;
    } catch (e) {
      log('Failed to connect: ' + e.message, 'err');
      return false;
    }
  }

  /**
   * Disconnect from current shared world
   */
  function disconnect() {
    if (socket) {
      socket.close();
      log('Disconnected from shared world: ' + worldId, 'ok');
      socket = null;
      userId = null;
      worldId = null;
      return true;
    } else {
      log('Not connected to any shared world', 'dim');
      return false;
    }
  }

  /**
   * Send a chat message
   * @param {string} message - Message to send
   */
  function say(message) {
    if (!isConnected()) {
      log('Not connected. Use "connect" first.', 'err');
      return false;
    }
    if (!message) {
      log('Usage: say <message>', 'dim');
      return false;
    }
    socket.send(JSON.stringify({ type: 'CHAT', message }));
    log('[you]: ' + message, 'ok');
    return true;
  }

  /**
   * Broadcast object creation to connected clients
   * @param {string} id - Object ID/name
   * @param {Object} data - Object data (type, x, y, z, color, size)
   */
  function broadcastCreate(id, data) {
    if (!isConnected()) return false;
    // Use flat format matching Three.js: object_type at top level
    const msg = {
      type: 'CREATE',
      id: id,
      object_type: data.type || 'cube',
      x: data.x,
      y: data.y,
      z: data.z || 0,
      color: data.color,
      size: data.size
    };
    console.log('[RoshNetwork] Sending CREATE:', msg);
    socket.send(JSON.stringify(msg));
    return true;
  }

  /**
   * Broadcast object deletion to connected clients
   * @param {string} id - Object ID/name
   */
  function broadcastDelete(id) {
    if (!isConnected()) return false;
    socket.send(JSON.stringify({ type: 'DELETE', id }));
    return true;
  }

  /**
   * Broadcast object move to connected clients
   * @param {string} id - Object ID/name
   * @param {Object} position - {x, y, z}
   */
  function broadcastMove(id, position) {
    if (!isConnected()) return false;
    socket.send(JSON.stringify({ type: 'MOVE', id, ...position }));
    return true;
  }

  /**
   * Request list of users in current world
   */
  function listUsers() {
    if (!isConnected()) {
      log('Not connected. Use "connect" first.', 'err');
      return false;
    }
    socket.send(JSON.stringify({ type: 'USERS' }));
    return true;
  }

  /**
   * Handle incoming messages from server
   */
  function handleMessage(msg) {
    console.log('[RoshNetwork] Received:', msg.type, msg);
    switch (msg.type) {
      case 'CONNECTED':
        userId = msg.user_id;
        log('Connected to "' + worldId + '" as user ' + msg.user_id, 'ok');
        log('Objects you create will be shared with others!', 'cyan');
        break;

      case 'OBJECT_CREATED':
        if (msg.by !== userId) {
          const data = msg.data || {};
          // Build human-readable command description
          const sizeWord = data.size ? data.size + ' ' : '';
          const colorWord = data.color ? data.color + ' ' : '';
          const typeWord = data.type || 'object';
          const cmdDesc = 'create a ' + sizeWord + colorWord + typeWord;

          // Log clearly what was received
          log('[' + msg.by.slice(0,6) + '] sent: ' + cmdDesc, 'cyan');

          // Attempt to render
          if (adapter.createObject) {
            adapter.createObject(data.type || 'sphere', msg.id, {
              x: data.x, y: data.y, z: data.z,
              color: data.color,
              size: data.size
            });
          } else {
            log('  (cannot render - no adapter)', 'dim');
          }
        }
        break;

      case 'OBJECT_DELETED':
        if (msg.by !== userId) {
          log('[' + msg.by.slice(0,6) + '] sent: delete ' + msg.id, 'cyan');
          if (adapter.deleteObject) {
            adapter.deleteObject(msg.id);
          } else {
            log('  (cannot render - no adapter)', 'dim');
          }
        }
        break;

      case 'OBJECT_MOVED':
        if (msg.by !== userId) {
          log('[' + msg.by.slice(0,6) + '] sent: move ' + msg.id + ' to (' + msg.x + ', ' + msg.y + ')', 'dim');
          if (adapter.moveObject) {
            adapter.moveObject(msg.id, { x: msg.x, y: msg.y, z: msg.z });
          }
        }
        break;

      case 'CHAT':
        log('[' + msg.by + ']: ' + msg.message, 'cyan');
        break;

      case 'WORLD_STATE':
        const objects = msg.objects || {};
        const count = Object.keys(objects).length;
        if (count > 0) {
          log('Loading ' + count + ' shared object(s) from world...', 'dim');
          for (const [id, data] of Object.entries(objects)) {
            // Build human-readable description
            const sizeWord = data.size ? data.size + ' ' : '';
            const colorWord = data.color ? data.color + ' ' : '';
            const typeWord = data.type || 'object';
            log('  - ' + id + ': ' + sizeWord + colorWord + typeWord, 'dim');

            if (adapter.createObject) {
              adapter.createObject(data.type || 'sphere', id, {
                x: data.x, y: data.y, z: data.z,
                color: data.color,
                size: data.size
              });
            }
          }
        } else {
          log('World is empty - you can create objects!', 'dim');
        }
        break;

      case 'USERS_LIST':
        log('=== Users in "' + msg.world_id + '" (' + msg.count + ') ===', 'cyan');
        for (const user of msg.users) {
          const youTag = user.is_you ? ' (you)' : '';
          log('  ' + user.id + youTag, user.is_you ? 'ok' : 'dim');
        }
        break;

      case 'USER_JOINED':
        log('[' + msg.user_id + '] joined (' + msg.user_count + ' users)', 'cyan');
        break;

      case 'USER_LEFT':
        log('[' + msg.user_id + '] left (' + msg.user_count + ' users)', 'dim');
        break;

      default:
        console.log('Unknown message type:', msg.type);
    }
  }

  // Public API
  return {
    init,
    connect,
    disconnect,
    say,
    isConnected,
    getConnectionInfo,
    broadcastCreate,
    broadcastDelete,
    broadcastMove,
    listUsers
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RoshNetwork;
}
