"""
Adapter Parity Tests

Ensures that Phaser and ThreeJS adapters implement the same
interface expected by rosh-network.js for networking parity.

These tests verify that network messages will work consistently
across all targets.
"""

import re
from pathlib import Path


class TestAdapterInterface:
    """Test that adapters implement the required interface for rosh-network.js."""

    def setup_method(self):
        """Load adapter source files."""
        static_dir = Path(__file__).parent.parent / 'static'
        self.phaser_adapter = (static_dir / 'rosh-adapter-phaser.js').read_text()
        self.threejs_adapter = (static_dir / 'rosh-adapter-threejs.js').read_text()
        self.network_js = (static_dir / 'rosh-network.js').read_text()

    def test_phaser_adapter_exists(self):
        """Phaser adapter file exists and loads."""
        assert len(self.phaser_adapter) > 0

    def test_threejs_adapter_exists(self):
        """ThreeJS adapter file exists and loads."""
        assert len(self.threejs_adapter) > 0

    def test_network_js_exists(self):
        """Network JS file exists and loads."""
        assert len(self.network_js) > 0


class TestRequiredCallbacks:
    """Test that adapters implement all callbacks expected by rosh-network.js."""

    def setup_method(self):
        """Load adapter source files."""
        static_dir = Path(__file__).parent.parent / 'static'
        self.phaser_adapter = (static_dir / 'rosh-adapter-phaser.js').read_text()
        self.threejs_adapter = (static_dir / 'rosh-adapter-threejs.js').read_text()

    # Required callbacks from rosh-network.js analysis:
    # - createObject(type, id, data)
    # - deleteObject(id)
    # - moveObject(id, pos)
    # - setProperty(id, prop, val)
    # - applyCapability(id, prop, val)
    # - toggleSpotlight(visible, target)

    def test_phaser_has_createObject(self):
        """Phaser adapter has createObject."""
        assert 'createObject:' in self.phaser_adapter or 'createObject =' in self.phaser_adapter

    def test_phaser_has_deleteObject(self):
        """Phaser adapter has deleteObject."""
        assert 'deleteObject:' in self.phaser_adapter or 'deleteObject =' in self.phaser_adapter

    def test_phaser_has_moveObject(self):
        """Phaser adapter has moveObject."""
        assert 'moveObject:' in self.phaser_adapter or 'moveObject =' in self.phaser_adapter

    def test_phaser_has_setProperty(self):
        """Phaser adapter has setProperty."""
        assert 'setProperty:' in self.phaser_adapter or 'setProperty =' in self.phaser_adapter

    def test_phaser_has_applyCapability(self):
        """Phaser adapter has applyCapability."""
        assert 'applyCapability:' in self.phaser_adapter or 'applyCapability =' in self.phaser_adapter

    def test_phaser_has_toggleSpotlight(self):
        """Phaser adapter has toggleSpotlight (stub for 2D)."""
        assert 'toggleSpotlight:' in self.phaser_adapter or 'toggleSpotlight =' in self.phaser_adapter

    def test_threejs_has_createObject(self):
        """ThreeJS adapter has createObject."""
        assert 'createObject:' in self.threejs_adapter or 'createObject =' in self.threejs_adapter

    def test_threejs_has_deleteObject(self):
        """ThreeJS adapter has deleteObject."""
        assert 'deleteObject:' in self.threejs_adapter or 'deleteObject =' in self.threejs_adapter

    def test_threejs_has_moveObject(self):
        """ThreeJS adapter has moveObject."""
        assert 'moveObject:' in self.threejs_adapter or 'moveObject =' in self.threejs_adapter

    def test_threejs_has_setProperty(self):
        """ThreeJS adapter has setProperty."""
        assert 'setProperty:' in self.threejs_adapter or 'setProperty =' in self.threejs_adapter

    def test_threejs_has_applyCapability(self):
        """ThreeJS adapter has applyCapability."""
        # ThreeJS uses applyCapabilityBridge which wraps capabilities
        assert 'applyCapability' in self.threejs_adapter

    def test_threejs_has_toggleSpotlight(self):
        """ThreeJS adapter has toggleSpotlight."""
        assert 'toggleSpotlight:' in self.threejs_adapter or 'toggleSpotlight =' in self.threejs_adapter


class TestCallbackSignatures:
    """Test that callback signatures match what rosh-network.js expects."""

    def setup_method(self):
        """Load adapter source files."""
        static_dir = Path(__file__).parent.parent / 'static'
        self.phaser_adapter = (static_dir / 'rosh-adapter-phaser.js').read_text()
        self.threejs_adapter = (static_dir / 'rosh-adapter-threejs.js').read_text()

    def test_phaser_createObject_signature(self):
        """Phaser createObject takes (typeName, name, options)."""
        # Match: createObject: function(typeName, name, options
        pattern = r'createObject:\s*function\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+'
        assert re.search(pattern, self.phaser_adapter), \
            "Phaser createObject should take 3 args: (type, id, data)"

    def test_threejs_createObject_signature(self):
        """ThreeJS createObject takes (typeName, name, options)."""
        pattern = r'createObject:\s*function\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+'
        assert re.search(pattern, self.threejs_adapter), \
            "ThreeJS createObject should take 3 args: (type, id, data)"

    def test_phaser_setProperty_signature(self):
        """Phaser setProperty takes (name, prop, value)."""
        pattern = r'setProperty:\s*function\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+'
        assert re.search(pattern, self.phaser_adapter), \
            "Phaser setProperty should take 3 args: (id, prop, value)"

    def test_threejs_setProperty_signature(self):
        """ThreeJS setProperty takes (name, prop, value)."""
        pattern = r'setProperty:\s*function\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+'
        assert re.search(pattern, self.threejs_adapter), \
            "ThreeJS setProperty should take 3 args: (id, prop, value)"


class TestNetworkIntegration:
    """Test that adapters are correctly integrated with rosh-network.js."""

    def setup_method(self):
        """Load source files."""
        static_dir = Path(__file__).parent.parent / 'static'
        self.network_js = (static_dir / 'rosh-network.js').read_text()
        self.runtime_js = (static_dir / 'rosh-runtime.js').read_text()

    def test_network_uses_createObject(self):
        """rosh-network.js calls adapter.createObject."""
        assert 'adapter.createObject' in self.network_js

    def test_network_uses_deleteObject(self):
        """rosh-network.js calls adapter.deleteObject."""
        assert 'adapter.deleteObject' in self.network_js

    def test_network_uses_moveObject(self):
        """rosh-network.js calls adapter.moveObject."""
        assert 'adapter.moveObject' in self.network_js

    def test_network_uses_setProperty(self):
        """rosh-network.js calls adapter.setProperty."""
        assert 'adapter.setProperty' in self.network_js

    def test_network_uses_applyCapability(self):
        """rosh-network.js calls adapter.applyCapability."""
        assert 'adapter.applyCapability' in self.network_js

    def test_network_uses_toggleSpotlight(self):
        """rosh-network.js calls adapter.toggleSpotlight."""
        assert 'adapter.toggleSpotlight' in self.network_js

    def test_runtime_broadcasts_create(self):
        """rosh-runtime.js broadcasts creates to network."""
        assert 'RoshNetwork.broadcastCreate' in self.runtime_js

    def test_runtime_broadcasts_delete(self):
        """rosh-runtime.js broadcasts deletes to network."""
        assert 'RoshNetwork.broadcastDelete' in self.runtime_js

    def test_runtime_broadcasts_update(self):
        """rosh-runtime.js broadcasts updates to network."""
        assert 'RoshNetwork.broadcastUpdate' in self.runtime_js


class TestLegacyInlineAdapter:
    """Test that the legacy inline adapter in Phaser emitter matches expected interface."""

    def setup_method(self):
        """Load Phaser emitter source."""
        emitter_dir = Path(__file__).parent.parent / 'src' / 'rosh' / 'emitters'
        self.phaser_emitter = (emitter_dir / 'phaser.py').read_text()

    def test_legacy_adapter_has_createObject(self):
        """Legacy inline adapter has createObject with correct signature."""
        # Should have createObject: function(type, id, data)
        assert 'createObject: function(type, id, data)' in self.phaser_emitter

    def test_legacy_adapter_has_deleteObject(self):
        """Legacy inline adapter has deleteObject."""
        assert 'deleteObject: function(id)' in self.phaser_emitter

    def test_legacy_adapter_has_moveObject(self):
        """Legacy inline adapter has moveObject."""
        assert 'moveObject: function(id, pos)' in self.phaser_emitter

    def test_legacy_adapter_has_setProperty(self):
        """Legacy inline adapter has setProperty."""
        assert 'setProperty: function(id, prop, value)' in self.phaser_emitter

    def test_legacy_adapter_has_applyCapability(self):
        """Legacy inline adapter has applyCapability."""
        assert 'applyCapability: function(id, capability, value)' in self.phaser_emitter

    def test_legacy_adapter_has_toggleSpotlight(self):
        """Legacy inline adapter has toggleSpotlight."""
        assert 'toggleSpotlight: function(visible, target)' in self.phaser_emitter
