"""
Unit tests for string methods (v0.0.5)

Tests split, substring, lowercase, uppercase, trim, indexOf, and lastIndexOf
"""

import pytest
from io import StringIO
from unittest.mock import patch
from src.rosh.lexer import Lexer
from src.rosh.parser import Parser
from src.rosh.interpreter import Interpreter


def run_rosh(code):
    """Helper to run Rosh code and capture output"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    # Capture print output using a StringIO stream
    captured_output = StringIO()
    interpreter = Interpreter(output_stream=captured_output)

    interpreter.execute(ast)

    # Split output by newlines and filter empty strings
    output_text = captured_output.getvalue()
    if output_text:
        output = [line for line in output_text.split('\n') if line]
    else:
        output = []

    return output, interpreter


class TestStringSplit:
    """Test split string by delimiter"""

    def test_split_by_comma(self):
        """Split comma-separated values"""
        code = """
        create string csv to "apple,banana,cherry"
        create string fruits to split csv by ","
        print fruits
        """
        output, _ = run_rosh(code)
        assert output == ["['apple', 'banana', 'cherry']"]

    def test_split_by_space(self):
        """Split space-separated words"""
        code = """
        create string sentence to "hello world test"
        create string words to split sentence by " "
        print words
        """
        output, _ = run_rosh(code)
        assert output == ["['hello', 'world', 'test']"]

    def test_split_single_word(self):
        """Split single word with no delimiter"""
        code = """
        create string word to "hello"
        create string parts to split word by ","
        print parts
        """
        output, _ = run_rosh(code)
        assert output == ["['hello']"]

    def test_split_empty_string(self):
        """Split empty string"""
        code = """
        create string empty to ""
        create string parts to split empty by ","
        print parts
        """
        output, _ = run_rosh(code)
        assert output == ["['']"]

    def test_split_iterate(self):
        """Split and iterate through results"""
        code = """
        create string data to "a,b,c"
        create string parts to split data by ","
        for part in parts then
            print part
        end
        """
        output, _ = run_rosh(code)
        assert output == ['a', 'b', 'c']


class TestSubstring:
    """Test substring extraction"""

    def test_substring_beginning(self):
        """Extract substring from beginning"""
        code = """
        create string text to "Hello World"
        create string sub to substring of text from 0 length 5
        print sub
        """
        output, _ = run_rosh(code)
        assert output == ['Hello']

    def test_substring_middle(self):
        """Extract substring from middle"""
        code = """
        create string text to "Hello World"
        create string sub to substring of text from 6 length 5
        print sub
        """
        output, _ = run_rosh(code)
        assert output == ['World']

    def test_substring_single_char(self):
        """Extract single character"""
        code = """
        create string text to "Hello"
        create string char to substring of text from 1 length 1
        print char
        """
        output, _ = run_rosh(code)
        assert output == ['e']

    def test_substring_entire_string(self):
        """Extract entire string"""
        code = """
        create string text to "test"
        create string full to substring of text from 0 length 4
        print full
        """
        output, _ = run_rosh(code)
        assert output == ['test']

    def test_substring_beyond_length(self):
        """Extract substring with length beyond string"""
        code = """
        create string text to "Hi"
        create string sub to substring of text from 0 length 100
        print sub
        """
        output, _ = run_rosh(code)
        assert output == ['Hi']


class TestCaseConversion:
    """Test lowercase and uppercase"""

    def test_lowercase(self):
        """Convert to lowercase"""
        code = """
        create string text to "HELLO WORLD"
        create string lower to lowercase of text
        print lower
        """
        output, _ = run_rosh(code)
        assert output == ['hello world']

    def test_uppercase(self):
        """Convert to uppercase"""
        code = """
        create string text to "hello world"
        create string upper to uppercase of text
        print upper
        """
        output, _ = run_rosh(code)
        assert output == ['HELLO WORLD']

    def test_lowercase_mixed(self):
        """Convert mixed case to lowercase"""
        code = """
        create string text to "HeLLo WoRLd"
        create string lower to lowercase of text
        print lower
        """
        output, _ = run_rosh(code)
        assert output == ['hello world']

    def test_uppercase_mixed(self):
        """Convert mixed case to uppercase"""
        code = """
        create string text to "HeLLo WoRLd"
        create string upper to uppercase of text
        print upper
        """
        output, _ = run_rosh(code)
        assert output == ['HELLO WORLD']

    def test_case_with_numbers(self):
        """Case conversion with numbers"""
        code = """
        create string text to "Test123"
        create string lower to lowercase of text
        create string upper to uppercase of text
        print lower
        print upper
        """
        output, _ = run_rosh(code)
        assert output == ['test123', 'TEST123']

    def test_case_normalization(self):
        """Use case conversion for normalization"""
        code = """
        set text to "GO NORTH"
        set normalized to lowercase of text
        if normalized is equal to "go north" then
            print "matched"
        end
        """
        output, _ = run_rosh(code)
        assert output == ['matched']


class TestTrim:
    """Test whitespace trimming"""

    def test_trim_both_sides(self):
        """Trim whitespace from both sides"""
        code = """
        create string text to "  hello  "
        create string trimmed to trim text
        print trimmed
        """
        output, _ = run_rosh(code)
        assert output == ['hello']

    def test_trim_left_only(self):
        """Trim whitespace from left"""
        code = """
        create string text to "  hello"
        create string trimmed to trim text
        print trimmed
        """
        output, _ = run_rosh(code)
        assert output == ['hello']

    def test_trim_right_only(self):
        """Trim whitespace from right"""
        code = """
        create string text to "hello  "
        create string trimmed to trim text
        print trimmed
        """
        output, _ = run_rosh(code)
        assert output == ['hello']

    def test_trim_no_whitespace(self):
        """Trim string with no whitespace"""
        code = """
        create string text to "hello"
        create string trimmed to trim text
        print trimmed
        """
        output, _ = run_rosh(code)
        assert output == ['hello']

    def test_trim_tabs_newlines(self):
        """Trim tabs and newlines"""
        code = """
        create string text to "	hello	"
        create string trimmed to trim text
        print trimmed
        """
        output, _ = run_rosh(code)
        assert output == ['hello']


class TestIndexOf:
    """Test indexOf and lastIndexOf"""

    def test_indexof_found(self):
        """Find substring at beginning"""
        code = """
        create string text to "hello world"
        create number pos to indexOf "hello" in text
        print pos
        """
        output, _ = run_rosh(code)
        assert output == ['0']

    def test_indexof_middle(self):
        """Find substring in middle"""
        code = """
        create string text to "The quick brown fox"
        create number pos to indexOf "quick" in text
        print pos
        """
        output, _ = run_rosh(code)
        assert output == ['4']

    def test_indexof_not_found(self):
        """Search for substring not in string"""
        code = """
        create string text to "hello world"
        create number pos to indexOf "xyz" in text
        print pos
        """
        output, _ = run_rosh(code)
        assert output == ['-1']

    def test_indexof_case_sensitive(self):
        """indexOf is case-sensitive"""
        code = """
        create string text to "Hello World"
        create number pos1 to indexOf "hello" in text
        create number pos2 to indexOf "Hello" in text
        print pos1
        print pos2
        """
        output, _ = run_rosh(code)
        assert output == ['-1', '0']

    def test_lastindexof_multiple_occurrences(self):
        """Find last occurrence of substring"""
        code = """
        create string text to "hello world hello"
        create number first to indexOf "hello" in text
        create number last to lastIndexOf "hello" in text
        print first
        print last
        """
        output, _ = run_rosh(code)
        assert output == ['0', '12']

    def test_lastindexof_single_occurrence(self):
        """lastIndexOf with single occurrence"""
        code = """
        create string text to "hello world"
        create number pos to lastIndexOf "world" in text
        print pos
        """
        output, _ = run_rosh(code)
        assert output == ['6']

    def test_lastindexof_not_found(self):
        """lastIndexOf when not found"""
        code = """
        create string text to "hello world"
        create number pos to lastIndexOf "xyz" in text
        print pos
        """
        output, _ = run_rosh(code)
        assert output == ['-1']

    def test_indexof_check_exists(self):
        """Use indexOf to check if substring exists"""
        code = """
        create string command to "take sword from chest"
        create number pos to indexOf "sword" in command
        if pos is above -1 then
            print "found"
        end
        """
        output, _ = run_rosh(code)
        assert output == ['found']


class TestStringMethodsCombined:
    """Test combining multiple string methods"""

    def test_split_and_lowercase(self):
        """Split then convert to lowercase"""
        code = """
        set text to "GO NORTH"
        set words to split text by " "
        for word in words then
            set lower to lowercase of word
            print lower
        end
        """
        output, _ = run_rosh(code)
        assert output == ['go', 'north']

    def test_trim_and_split(self):
        """Trim then split"""
        code = """
        set text to "  a,b,c  "
        set trimmed to trim text
        set parts to split trimmed by ","
        print parts
        """
        output, _ = run_rosh(code)
        assert output == ["['a', 'b', 'c']"]

    def test_substring_and_uppercase(self):
        """Extract substring and convert to uppercase"""
        code = """
        create string text to "hello world"
        create string sub to substring of text from 0 length 5
        create string upper to uppercase of sub
        print upper
        """
        output, _ = run_rosh(code)
        assert output == ['HELLO']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
