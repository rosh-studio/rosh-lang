"""
Tests for TOON (Token-Oriented Object Notation) encoding and decoding
"""

import pytest
from src.rosh.toon_encoder import encode_toon, toon_output, save_as_toon
from src.rosh.toon_decoder import decode_toon, load_from_toon, TOONDecodeError
from src.rosh.values import RoshObject
import tempfile
import os


class TestTOONEncoder:
    """Tests for TOON encoding functionality"""

    def test_encode_none(self):
        """Test encoding None as TOON"""
        assert encode_toon(None) == "null"

    def test_encode_boolean(self):
        """Test encoding booleans as TOON"""
        assert encode_toon(True) == "true"
        assert encode_toon(False) == "false"

    def test_encode_number(self):
        """Test encoding numbers as TOON"""
        assert encode_toon(42) == "42"
        assert encode_toon(3.14) == "3.14"
        assert encode_toon(0) == "0"
        assert encode_toon(-10) == "-10"

    def test_encode_string_simple(self):
        """Test encoding simple strings as TOON"""
        assert encode_toon("hello") == "hello"
        assert encode_toon("world") == "world"

    def test_encode_string_with_special_chars(self):
        """Test encoding strings with special characters"""
        # Strings with commas need quoting
        assert encode_toon("hello, world") == '"hello, world"'
        # Strings with colons need quoting
        assert encode_toon("key: value") == '"key: value"'
        # Strings with newlines need quoting (newline preserved in quoted string)
        result = encode_toon("line1\nline2")
        assert result.startswith('"')
        assert result.endswith('"')
        assert "line1" in result
        assert "line2" in result

    def test_encode_simple_list(self):
        """Test encoding simple list as TOON CSV format"""
        result = encode_toon(["red", "green", "blue"])
        assert result == "value[3]: red,green,blue"

        result = encode_toon([1, 2, 3, 4])
        assert result == "value[4]: 1,2,3,4"

    def test_encode_empty_list(self):
        """Test encoding empty list"""
        result = encode_toon([])
        assert result == "value[0]:"

    def test_encode_simple_dict(self):
        """Test encoding simple dictionary as TOON"""
        result = encode_toon({"name": "John", "age": 30})
        lines = result.split('\n')
        assert "name: John" in lines
        assert "age: 30" in lines

    def test_encode_nested_dict(self):
        """Test encoding nested dictionary as TOON"""
        data = {
            "person": {
                "name": "John",
                "age": 30
            },
            "city": "Boulder"
        }
        result = encode_toon(data)
        assert "person:" in result
        assert "name: John" in result
        assert "age: 30" in result
        assert "city: Boulder" in result

    def test_encode_rosh_object_simple(self):
        """Test encoding simple RoshObject as TOON"""
        obj = RoshObject("game")
        obj.set("name", "test")
        obj.set("score", 100)

        result = encode_toon(obj)
        assert "# object: game" in result
        assert "name: test" in result
        assert "score: 100" in result
        assert "_uuid:" in result
        assert "_name: game" in result

    def test_encode_rosh_object_nested(self):
        """Test encoding nested RoshObjects as TOON"""
        player = RoshObject("player")
        player.set("name", "Alice")
        player.set("health", 100)

        game = RoshObject("game")
        game.set("title", "Dungeon")
        game.set("player", player)

        result = encode_toon(game)
        assert "# object: game" in result
        assert "title: Dungeon" in result
        assert "player:" in result
        assert "name: Alice" in result
        assert "health: 100" in result

    def test_encode_dict_with_list(self):
        """Test encoding dictionary containing list"""
        data = {
            "name": "game",
            "players": ["alice", "bob", "charlie"]
        }
        result = encode_toon(data)
        assert "name: game" in result
        assert "players:" in result
        assert "value[3]: alice,bob,charlie" in result

    def test_toon_output(self):
        """Test toon_output wrapper function"""
        data = {"test": "value"}
        result = toon_output(data)
        assert "test: value" in result

    def test_save_as_toon(self):
        """Test saving TOON to file"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toon', delete=False) as f:
            filepath = f.name

        try:
            # Save data as TOON
            data = {
                "name": "test",
                "score": 100
            }
            save_as_toon(filepath, data)

            # Read back and verify
            with open(filepath, 'r') as f:
                content = f.read()

            assert "name: test" in content
            assert "score: 100" in content

        finally:
            # Clean up
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_encode_list_with_commas_in_strings(self):
        """Test encoding list with strings containing commas"""
        result = encode_toon(["hello, world", "foo", "bar"])
        assert 'value[3]: "hello, world",foo,bar' in result

    def test_encode_dict_indentation(self):
        """Test that nested dicts have proper indentation"""
        data = {
            "level1": {
                "level2": {
                    "value": "deep"
                }
            }
        }
        result = encode_toon(data)
        lines = result.split('\n')

        # Check indentation increases with nesting
        level1_line = [l for l in lines if l.strip().startswith("level1:")][0]
        level2_line = [l for l in lines if l.strip().startswith("level2:")][0]
        value_line = [l for l in lines if l.strip().startswith("value:")][0]

        # level2 should have more leading spaces than level1
        assert len(level2_line) - len(level2_line.lstrip()) > len(level1_line) - len(level1_line.lstrip())
        # value should have more leading spaces than level2
        assert len(value_line) - len(value_line.lstrip()) > len(level2_line) - len(level2_line.lstrip())


class TestTOONDecoder:
    """Tests for TOON decoding functionality"""

    def test_decode_none(self):
        """Test decoding null"""
        assert decode_toon("null") is None

    def test_decode_boolean(self):
        """Test decoding booleans"""
        assert decode_toon("true") is True
        assert decode_toon("false") is False

    def test_decode_number(self):
        """Test decoding numbers"""
        assert decode_toon("42") == 42
        assert decode_toon("3.14") == 3.14
        assert decode_toon("0") == 0
        assert decode_toon("-10") == -10

    def test_decode_string_simple(self):
        """Test decoding simple strings"""
        assert decode_toon("hello") == "hello"
        assert decode_toon("world") == "world"

    def test_decode_string_quoted(self):
        """Test decoding quoted strings with special characters"""
        assert decode_toon('"hello, world"') == "hello, world"
        assert decode_toon('"key: value"') == "key: value"

    def test_decode_string_with_escapes(self):
        """Test decoding strings with escape sequences"""
        assert decode_toon(r'"line1\nline2"') == "line1\nline2"
        assert decode_toon(r'"quote: \"hello\""') == 'quote: "hello"'
        assert decode_toon(r'"backslash: \\"') == "backslash: \\"

    def test_decode_simple_array(self):
        """Test decoding CSV-style arrays"""
        assert decode_toon("value[3]: red,green,blue") == ["red", "green", "blue"]
        assert decode_toon("value[2]: 1,2") == [1, 2]
        assert decode_toon("value[0]:") == []

    def test_decode_array_with_quoted_strings(self):
        """Test decoding arrays with quoted items"""
        result = decode_toon('value[2]: "hello, world","foo: bar"')
        assert result == ["hello, world", "foo: bar"]

    def test_decode_simple_dict(self):
        """Test decoding simple key-value pairs"""
        toon = "name: John\nage: 30"
        result = decode_toon(toon)
        assert result == {"name": "John", "age": 30}

    def test_decode_nested_dict(self):
        """Test decoding nested objects"""
        toon = """player:
  name: Alice
  score: 100"""
        result = decode_toon(toon)
        assert result == {
            "player": {
                "name": "Alice",
                "score": 100
            }
        }

    def test_decode_rosh_object(self):
        """Test decoding RoshObject"""
        toon = """# object: player
name: Bob
health: 100"""
        result = decode_toon(toon)
        assert isinstance(result, RoshObject)
        assert result.name == "player"
        assert result.get("name") == "Bob"
        assert result.get("health") == 100

    def test_decode_multiline_array(self):
        """Test decoding multi-line array with nested objects"""
        toon = """value[2]:
  # object: player
  name: Alice
  score: 100
  # object: player
  name: Bob
  score: 200"""
        result = decode_toon(toon)
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], RoshObject)
        assert result[0].get("name") == "Alice"
        assert result[1].get("name") == "Bob"


class TestTOONRoundTrip:
    """Tests for TOON encode/decode round-trip"""

    def test_roundtrip_primitives(self):
        """Test encoding and decoding primitives"""
        for value in [None, True, False, 42, 3.14, "hello"]:
            encoded = encode_toon(value)
            decoded = decode_toon(encoded)
            assert decoded == value

    def test_roundtrip_simple_array(self):
        """Test encoding and decoding simple arrays"""
        original = ["red", "green", "blue"]
        encoded = encode_toon(original)
        decoded = decode_toon(encoded)
        assert decoded == original

    def test_roundtrip_dict(self):
        """Test encoding and decoding dicts"""
        original = {"name": "John", "age": 30, "active": True}
        encoded = encode_toon(original)
        decoded = decode_toon(encoded)
        assert decoded == original

    def test_roundtrip_nested_dict(self):
        """Test encoding and decoding nested dicts"""
        original = {
            "player": {
                "name": "Alice",
                "stats": {
                    "health": 100,
                    "mana": 50
                }
            }
        }
        encoded = encode_toon(original)
        decoded = decode_toon(encoded)
        assert decoded == original

    def test_roundtrip_rosh_object(self):
        """Test encoding and decoding RoshObject"""
        original = RoshObject("game")
        original.set("title", "My Game")
        original.set("version", "v1.0")  # Use string that won't be parsed as number
        original.set("players", 2)

        encoded = encode_toon(original)
        decoded = decode_toon(encoded)

        assert isinstance(decoded, RoshObject)
        assert decoded.name == "game"
        assert decoded.get("title") == "My Game"
        assert decoded.get("version") == "v1.0"
        assert decoded.get("players") == 2

    def test_roundtrip_complex_state(self):
        """Test encoding and decoding complex game state"""
        player = RoshObject("player")
        player.set("name", "Hero")
        player.set("health", 100)
        player.set("inventory", ["sword", "shield"])

        state = {
            "player": player,
            "score": 1000,
            "level": 5
        }

        encoded = encode_toon(state)
        decoded = decode_toon(encoded)

        assert decoded["score"] == 1000
        assert decoded["level"] == 5
        assert isinstance(decoded["player"], RoshObject)
        assert decoded["player"].get("name") == "Hero"
        assert decoded["player"].get("inventory") == ["sword", "shield"]


class TestTOONFileOperations:
    """Tests for TOON file save/load operations"""

    def test_save_and_load_toon_file(self):
        """Test saving and loading TOON files"""
        state = {
            "name": "Test",
            "value": 42,
            "items": ["a", "b", "c"]
        }

        # Create a temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toon', delete=False) as f:
            temp_path = f.name

        try:
            # Save
            save_as_toon(temp_path, state)

            # Load
            loaded = load_from_toon(temp_path)

            # Verify
            assert loaded == state
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestTOONIntegration:
    """Integration tests for TOON with Rosh interpreter"""

    def test_toon_cli_flag(self):
        """Test --toon CLI flag (integration test)"""
        # This would require running the actual CLI
        # For now, we test the encoder components directly
        pass

    def test_save_load_toon_file(self):
        """Test save/load with .toon extension (integration test)"""
        # This would test the interpreter's save/load commands
        # Deferred to full integration test suite
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
