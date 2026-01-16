/**
 * Rosh Network Module - Project Twin Multiplayer
 *
 * Implements REQUEST/CONFIRMED protocol (Spec 0.3):
 * - Clients send REQUEST_* messages
 * - Server validates and broadcasts CONFIRMED_* to ALL clients
 * - Clients apply changes ONLY on CONFIRMED (not on send)
 *
 * Usage:
 *   const network = RoshNetwork.init({ adapter, log, serverUrl });
 *   network.connect('worldName');
 *   network.requestCreate('ball', { type: 'sphere', color: 'red' });
 */

const RoshNetwork = (function() {
  'use strict';

  // Default server URL - auto-detect localhost
  const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  const DEFAULT_SERVER = isLocalhost
    ? 'ws://' + window.location.host + '/ws/world/'
    : 'wss://rosh.cloud/ws/world/';

  // Module state
  let socket = null;
  let userId = null;
  let displayName = null;  // User's display name (username if logged in)
  let worldId = null;
  let serverUrl = DEFAULT_SERVER;
  let adapter = null;
  let log = console.log;

  // Map of user_id -> display_name for all users in world
  const userDisplayNames = new Map();

  // Pending requests (for tracking)
  const pendingRequests = new Map();  // request_id -> { type, id, data, callback }

  /**
   * Generate a unique request ID
   */
  function generateRequestId() {
    return 'req_' + Math.random().toString(36).substr(2, 9);
  }

  /**
   * Get display name for a user_id (falls back to truncated user_id)
   */
  function getDisplayName(uid) {
    return userDisplayNames.get(uid) || uid.slice(0, 6);
  }

  /**
   * Initialize the network module
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
      userId: userId,
      displayName: displayName
    };
  }

  /**
   * Connect to a shared world
   */
  function connect(world = 'default') {
    if (isConnected()) {
      log('Already connected to world: ' + worldId, 'warn');
      log('Use "disconnect" first to leave current world', 'dim');
      return false;
    }

    // Extract server name for display
    const serverDisplay = serverUrl.includes('localhost') ? 'localhost' :
                          serverUrl.includes('rosh.cloud') ? 'rosh.cloud' :
                          serverUrl.replace(/^wss?:\/\//, '').split('/')[0];
    log('Connecting to ' + world + ' on ' + serverDisplay + '...', 'cyan');

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
        displayName = null;
        worldId = null;
        pendingRequests.clear();
        userDisplayNames.clear();
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
      pendingRequests.clear();
      return true;
    } else {
      log('Not connected to any shared world', 'dim');
      return false;
    }
  }

  /**
   * Send a chat message
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

  // ========================================
  // REQUEST/CONFIRMED Protocol (Spec 0.3)
  // ========================================

  /**
   * Request to create an object (waits for CONFIRMED before applying)
   * @param {string} id - Object ID/name
   * @param {Object} data - Object data (type, x, y, z, color, size)
   * @param {string} rawCommand - Raw command for logging
   * @returns {string|false} request_id or false if not connected
   */
  function requestCreate(id, data, rawCommand) {
    if (!isConnected()) return false;

    const request_id = generateRequestId();
    const msg = {
      type: 'REQUEST_CREATE',
      request_id: request_id,
      id: id,
      object_type: data.type || 'cube',
      x: data.x,
      y: data.y,
      z: data.z || 0,
      color: data.color,
      size: data.size,
      cmd: rawCommand || null
    };

    pendingRequests.set(request_id, { type: 'create', id, data });
    console.log('[RoshNetwork] Sending REQUEST_CREATE:', msg);
    socket.send(JSON.stringify(msg));
    return request_id;
  }

  /**
   * Request to move an object
   */
  function requestMove(id, position) {
    if (!isConnected()) return false;

    const request_id = generateRequestId();
    const msg = {
      type: 'REQUEST_MOVE',
      request_id: request_id,
      id: id,
      x: position.x,
      y: position.y,
      z: position.z
    };

    pendingRequests.set(request_id, { type: 'move', id, position });
    socket.send(JSON.stringify(msg));
    return request_id;
  }

  /**
   * Request to update object properties
   */
  function requestUpdate(id, prop, value) {
    if (!isConnected()) return false;

    const request_id = generateRequestId();
    const changes = {};
    changes[prop] = value;

    const msg = {
      type: 'REQUEST_UPDATE',
      request_id: request_id,
      id: id,
      ...changes
    };

    pendingRequests.set(request_id, { type: 'update', id, changes });
    console.log('[RoshNetwork] Sending REQUEST_UPDATE:', msg);
    socket.send(JSON.stringify(msg));
    return request_id;
  }

  /**
   * Request to delete an object
   */
  function requestDelete(id) {
    if (!isConnected()) return false;

    const request_id = generateRequestId();
    const msg = {
      type: 'REQUEST_DELETE',
      request_id: request_id,
      id: id
    };

    pendingRequests.set(request_id, { type: 'delete', id });
    socket.send(JSON.stringify(msg));
    return request_id;
  }

  // ========================================
  // Legacy broadcast methods (backwards compatibility)
  // These use the old protocol - prefer request* methods
  // ========================================

  function broadcastCreate(id, data, rawCommand) {
    if (!isConnected()) return false;
    const msg = {
      type: 'CREATE',
      id: id,
      object_type: data.type || 'cube',
      x: data.x,
      y: data.y,
      z: data.z || 0,
      color: data.color,
      size: data.size,
      cmd: rawCommand || null
    };
    console.log('[RoshNetwork] Sending CREATE (legacy):', msg);
    socket.send(JSON.stringify(msg));
    return true;
  }

  function broadcastDelete(id) {
    if (!isConnected()) return false;
    socket.send(JSON.stringify({ type: 'DELETE', id }));
    return true;
  }

  function broadcastMove(id, position) {
    if (!isConnected()) return false;
    socket.send(JSON.stringify({ type: 'MOVE', id, ...position }));
    return true;
  }

  function broadcastUpdate(id, prop, value) {
    if (!isConnected()) return false;
    const changes = {};
    changes[prop] = value;
    socket.send(JSON.stringify({ type: 'UPDATE', id, ...changes }));
    console.log('[RoshNetwork] Sending UPDATE (legacy):', id, prop, value);
    return true;
  }

  function broadcastCommand(cmd) {
    if (!isConnected()) return false;
    socket.send(JSON.stringify({ type: 'COMMAND', cmd }));
    console.log('[RoshNetwork] Broadcasting command:', cmd);
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
        displayName = msg.display_name || msg.user_id;
        userDisplayNames.set(userId, displayName);
        // Also store any other users already in the world
        if (msg.state && msg.state.users) {
          for (const [uid, userData] of Object.entries(msg.state.users)) {
            if (userData.display_name) {
              userDisplayNames.set(uid, userData.display_name);
            }
          }
        }
        const connServerDisplay = serverUrl.includes('localhost') ? 'localhost' :
                                  serverUrl.includes('rosh.cloud') ? 'rosh.cloud' :
                                  serverUrl.replace(/^wss?:\/\//, '').split('/')[0];
        log('Connected to ' + worldId + ' on ' + connServerDisplay + ' as ' + displayName, 'ok');
        log('Objects you create will be shared with others!', 'cyan');
        break;

      // ========================================
      // CONFIRMED messages (Spec 0.3)
      // Apply to ALL clients including requester
      // ========================================

      case 'CONFIRMED_CREATE':
        {
          const data = msg.data || {};
          const objType = data.object_type || data.type || 'cube';
          const isOwnRequest = pendingRequests.has(msg.request_id);

          // Remove from pending
          pendingRequests.delete(msg.request_id);

          // Log
          if (isOwnRequest) {
            log('Created ' + msg.id + ' (seq=' + msg.seq + ')', 'ok');
          } else {
            const rawCmd = data.cmd;
            if (rawCmd) {
              log('[' + getDisplayName(msg.by) + '] ' + rawCmd + ' → ' + msg.id, 'cyan');
            } else {
              log('[' + getDisplayName(msg.by) + '] created ' + msg.id, 'cyan');
            }
          }

          // Apply to scene (ALL clients)
          if (adapter.createObject) {
            adapter.createObject(objType, msg.id, {
              x: data.x,
              y: data.y,
              z: data.z,
              color: data.color,
              size: data.size
            });
          }
        }
        break;

      case 'CONFIRMED_MOVE':
        {
          const isOwnRequest = pendingRequests.has(msg.request_id);
          pendingRequests.delete(msg.request_id);

          if (!isOwnRequest) {
            log('[' + getDisplayName(msg.by) + '] moved ' + msg.id, 'dim');
          }

          if (adapter.moveObject) {
            adapter.moveObject(msg.id, { x: msg.x, y: msg.y, z: msg.z });
          }
        }
        break;

      case 'CONFIRMED_UPDATE':
        {
          const isOwnRequest = pendingRequests.has(msg.request_id);
          pendingRequests.delete(msg.request_id);

          const changes = msg.changes || {};

          if (!isOwnRequest) {
            for (const [prop, val] of Object.entries(changes)) {
              log('[' + getDisplayName(msg.by) + '] set ' + msg.id + ' ' + prop + ' to ' + val, 'dim');
            }
          }

          // Apply changes
          for (const [prop, val] of Object.entries(changes)) {
            if (adapter.applyCapability && ['pulse', 'spin', 'bounce'].includes(prop)) {
              adapter.applyCapability(msg.id, prop, val);
            } else if (adapter.setProperty) {
              adapter.setProperty(msg.id, prop, val);
            }
          }
        }
        break;

      case 'CONFIRMED_DELETE':
        {
          const isOwnRequest = pendingRequests.has(msg.request_id);
          pendingRequests.delete(msg.request_id);

          if (isOwnRequest) {
            log('Deleted ' + msg.id, 'ok');
          } else {
            log('[' + getDisplayName(msg.by) + '] deleted ' + msg.id, 'cyan');
          }

          if (adapter.deleteObject) {
            adapter.deleteObject(msg.id);
          }
        }
        break;

      case 'REJECTED':
        {
          pendingRequests.delete(msg.request_id);
          log('Request rejected: ' + msg.message, 'err');
          console.log('[RoshNetwork] REJECTED:', msg);
        }
        break;

      // ========================================
      // Legacy message types (backwards compatibility)
      // ========================================

      case 'UPDATE':
        // Direct UPDATE from Python client (properties at top level, not in 'changes')
        if (msg.by !== userId) {
          const knownProps = ['x', 'y', 'z', 'visible', 'color', 'size', 'text', 'scale'];
          for (const prop of knownProps) {
            if (prop in msg && msg.id) {
              log('[' + (msg.by || 'remote').slice(0,6) + '] set ' + msg.id + ' ' + prop + ' to ' + msg[prop], 'dim');
              if (adapter.setProperty) {
                adapter.setProperty(msg.id, prop, msg[prop]);
              }
            }
          }
        }
        break;

      case 'OBJECT_CREATED':
        if (msg.by !== userId) {
          const data = msg.data || {};
          const objType = data.object_type || data.type || 'cube';

          const rawCmd = data.cmd;
          if (rawCmd) {
            log('[' + getDisplayName(msg.by) + '] ' + rawCmd + ' → ' + msg.id, 'cyan');
          } else {
            const sizeWord = data.size ? data.size + ' ' : '';
            const colorWord = data.color ? data.color + ' ' : '';
            log('[' + getDisplayName(msg.by) + '] create ' + msg.id + ' (' + sizeWord + colorWord + objType + ')', 'cyan');
          }

          if (adapter.createObject) {
            adapter.createObject(objType, msg.id, {
              x: data.x,
              y: data.y,
              z: data.z,
              color: data.color,
              size: data.size
            });
          }
        }
        break;

      case 'OBJECT_DELETED':
        if (msg.by !== userId) {
          log('[' + getDisplayName(msg.by) + '] sent: delete ' + msg.id, 'cyan');
          if (adapter.deleteObject) {
            adapter.deleteObject(msg.id);
          }
        }
        break;

      case 'OBJECT_MOVED':
        if (msg.by !== userId) {
          log('[' + getDisplayName(msg.by) + '] sent: move ' + msg.id + ' to (' + msg.x + ', ' + msg.y + ')', 'dim');
          if (adapter.moveObject) {
            adapter.moveObject(msg.id, { x: msg.x, y: msg.y, z: msg.z });
          }
        }
        break;

      case 'PROPERTY_UPDATED':
      case 'OBJECT_UPDATED':
        if (msg.by !== userId) {
          if (msg.id === '_spotlight') {
            const changes = msg.changes || {};
            if (adapter.toggleSpotlight) {
              if ('visible' in changes) {
                adapter.toggleSpotlight(changes.visible);
                log('[' + getDisplayName(msg.by) + '] spotlight ' + (changes.visible ? 'on' : 'off'), 'dim');
              }
              if ('target' in changes) {
                adapter.toggleSpotlight(true, changes.target);
                log('[' + getDisplayName(msg.by) + '] spotlight targeting ' + changes.target, 'dim');
              }
            }
            break;
          }
          const changes = msg.changes || {};
          for (const [prop, val] of Object.entries(changes)) {
            log('[' + getDisplayName(msg.by) + '] sent: set ' + msg.id + ' ' + prop + ' to ' + val, 'dim');
            if (adapter.applyCapability && ['pulse', 'spin', 'bounce'].includes(prop)) {
              adapter.applyCapability(msg.id, prop, val);
            } else if (adapter.setProperty) {
              adapter.setProperty(msg.id, prop, val);
            }
          }
        }
        break;

      case 'CHAT':
        log('[' + getDisplayName(msg.by) + ']: ' + msg.message, 'cyan');
        break;

      case 'WORLD_STATE':
        const objects = msg.objects || {};
        const count = Object.keys(objects).length;
        if (count > 0) {
          log('Loading ' + count + ' shared object(s) from world...', 'dim');
          for (const [id, data] of Object.entries(objects)) {
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
        if (msg.display_name) {
          userDisplayNames.set(msg.user_id, msg.display_name);
        }
        log('[' + getDisplayName(msg.user_id) + '] joined (' + msg.user_count + ' users)', 'cyan');
        break;

      case 'USER_LEFT':
        log('[' + getDisplayName(msg.user_id) + '] left (' + msg.user_count + ' users)', 'dim');
        userDisplayNames.delete(msg.user_id);
        break;

      case 'COMMAND':
        if (msg.by !== userId && msg.cmd) {
          console.log('[RoshNetwork] Executing remote command:', msg.cmd);
          if (typeof window !== 'undefined' && window.RoshRuntime && window.RoshRuntime.execCommand) {
            window.RoshRuntime.execCommand(msg.cmd, false);
          }
        }
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
    listUsers,
    // New REQUEST/CONFIRMED protocol (Spec 0.3)
    requestCreate,
    requestMove,
    requestUpdate,
    requestDelete,
    // Legacy broadcast methods (backwards compatibility)
    broadcastCreate,
    broadcastDelete,
    broadcastMove,
    broadcastUpdate,
    broadcastCommand
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RoshNetwork;
}
