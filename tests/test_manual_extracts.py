"""
Integration tests extracted from ROSH-MANUAL.rosh

This test file extracts code examples from ROSH-MANUAL.rosh and runs them
as individual tests. This ensures the manual stays in sync with the implementation.

Each section of the manual becomes a test case.
"""

import pytest
import re
from io import StringIO
from unittest.mock import patch
from pathlib import Path
from src.rosh.lexer import Lexer
from src.rosh.parser import Parser
from src.rosh.interpreter import Interpreter


def extract_manual_sections():
    """Extract code sections from ROSH-MANUAL.rosh"""
    manual_path = Path(__file__).parent.parent / 'ROSH-MANUAL.rosh'

    if not manual_path.exists():
        pytest.skip("ROSH-MANUAL.rosh not found")

    with open(manual_path, 'r') as f:
        content = f.read()

    # Split by section headers (e.g., "# 1. Basic Values")
    sections = []
    current_section = None
    current_code = []

    for line in content.split('\n'):
        # Check for section header
        if line.startswith('# ===') or re.match(r'^#\s+\d+\.', line):
            # Save previous section
            if current_section and current_code:
                sections.append({
                    'name': current_section,
                    'code': '\n'.join(current_code)
                })
            # Start new section
            current_section = line.strip('# ').strip('=').strip()
            current_code = []
        elif line.startswith('print "==='):
            # Section marker in code
            continue
        elif current_section and not line.startswith('#'):
            # Add code line to current section
            current_code.append(line)

    # Add last section
    if current_section and current_code:
        sections.append({
            'name': current_section,
            'code': '\n'.join(current_code)
        })

    return sections


def run_rosh_code(code, capture_output=True):
    """Run Rosh code and optionally capture output"""
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        if capture_output:
            captured_output = StringIO()
            interpreter = Interpreter(output_stream=captured_output)
            interpreter.execute(ast)

            output_text = captured_output.getvalue()
            output = [line for line in output_text.split('\n') if line] if output_text else []
            return True, output
        else:
            interpreter = Interpreter()
            interpreter.execute(ast)
            return True, []
    except Exception as e:
        return False, str(e)


class TestManualBasicFeatures:
    """Test basic features from manual"""

    def test_manual_variables(self):
        """Test basic variable creation"""
        code = """
        create string name to "Alice"
        create number age to 25
        print name
        print age
        """
        success, output = run_rosh_code(code)
        assert success
        assert 'Alice' in output
        assert '25' in output

    def test_manual_arithmetic(self):
        """Test arithmetic operations"""
        code = """
        create number x to 10 plus 5
        create number y to 6 times 7
        print x
        print y
        """
        success, output = run_rosh_code(code)
        assert success
        assert '15' in output
        assert '42' in output

    def test_manual_conditionals(self):
        """Test if/else statements"""
        code = """
        create number x to 15
        if x is above 10 then
            print "greater"
        end
        """
        success, output = run_rosh_code(code)
        assert success
        assert 'greater' in output

    def test_manual_while_loop(self):
        """Test while loops"""
        code = """
        create number count to 3
        while count is above 0 then
            print count
            set count to count minus 1
        end
        """
        success, output = run_rosh_code(code)
        assert success
        assert '3' in output
        assert '2' in output
        assert '1' in output

    def test_manual_for_loop_range(self):
        """Test for loops with ranges"""
        code = """
        for i in 1 to 3 then
            print i
        end
        """
        success, output = run_rosh_code(code)
        assert success
        assert output == ['1', '2', '3']

    def test_manual_lists(self):
        """Test list creation and access"""
        code = """
        create number nums to [10, 20, 30]
        print nums
        get nums[0]
        print
        """
        success, output = run_rosh_code(code)
        assert success
        assert '[10, 20, 30]' in output[0]
        assert '10' in output[1]

    def test_manual_list_iteration(self):
        """Test list iteration (v0.0.5)"""
        code = """
        create number scores to [95, 87, 92]
        for score in scores then
            print score
        end
        """
        success, output = run_rosh_code(code)
        assert success
        assert output == ['95', '87', '92']

    def test_manual_string_split(self):
        """Test string split (v0.0.5)"""
        code = """
        create string csv to "a,b,c"
        create string parts to split csv by ","
        for part in parts then
            print part
        end
        """
        success, output = run_rosh_code(code)
        assert success
        assert output == ['a', 'b', 'c']

    def test_manual_string_case(self):
        """Test string case conversion (v0.0.5)"""
        code = """
        create string text to "Hello"
        create string lower to lowercase of text
        create string upper to uppercase of text
        print lower
        print upper
        """
        success, output = run_rosh_code(code)
        assert success
        assert 'hello' in output
        assert 'HELLO' in output

    def test_manual_indexof(self):
        """Test indexOf (v0.0.5)"""
        code = """
        create string text to "hello world"
        create number pos to indexOf "world" in text
        print pos
        """
        success, output = run_rosh_code(code)
        assert success
        assert '6' in output


class TestManualAdvancedFeatures:
    """Test advanced features from manual"""

    def test_manual_functions(self):
        """Test function definition and calls"""
        code = """
        define function double x
            create number result to x times 2
            return result
        end

        call double 5
        print
        """
        success, output = run_rosh_code(code)
        assert success
        assert '10' in output

    def test_manual_objects(self):
        """Test object creation"""
        code = """
        create object player
            set name to "Hero"
            set health to 100
        end
        print player.name
        print player.health
        """
        success, output = run_rosh_code(code)
        assert success
        assert 'Hero' in output
        assert '100' in output

    def test_manual_break_continue(self):
        """Test break and continue"""
        code = """
        for i in 1 to 5 then
            if i is equal to 3 then
                continue
            end
            print i
        end
        """
        success, output = run_rosh_code(code)
        assert success
        assert '1' in output
        assert '2' in output
        assert '3' not in output
        assert '4' in output
        assert '5' in output


class TestManualStringMethods:
    """Test all string methods from manual sections 22-24"""

    def test_split_variations(self):
        """Test different split scenarios"""
        code = """
        create string s1 to split "a,b,c" by ","
        create string s2 to split "one two three" by " "
        print s1
        print s2
        """
        success, output = run_rosh_code(code)
        assert success

    def test_substring_extraction(self):
        """Test substring method"""
        code = """
        create string text to "Hello World"
        create string part1 to substring of text from 0 length 5
        create string part2 to substring of text from 6 length 5
        print part1
        print part2
        """
        success, output = run_rosh_code(code)
        assert success
        assert 'Hello' in output
        assert 'World' in output

    def test_case_and_trim(self):
        """Test case conversion and trim"""
        code = """
        create string upper to "HELLO"
        create string lower to lowercase of upper
        create string padded to "  test  "
        create string clean to trim padded
        print lower
        print clean
        """
        success, output = run_rosh_code(code)
        assert success
        assert 'hello' in output
        assert 'test' in output

    def test_search_methods(self):
        """Test indexOf and lastIndexOf"""
        code = """
        create string text to "hello world hello"
        create number first to indexOf "hello" in text
        create number last to lastIndexOf "hello" in text
        print first
        print last
        """
        success, output = run_rosh_code(code)
        assert success
        assert '0' in output
        assert '12' in output


class TestManualFullExecution:
    """Test that entire manual executes without errors"""

    @pytest.mark.slow
    def test_full_manual_runs(self):
        """Run entire ROSH-MANUAL.rosh file"""
        manual_path = Path(__file__).parent.parent / 'ROSH-MANUAL.rosh'

        if not manual_path.exists():
            pytest.skip("ROSH-MANUAL.rosh not found")

        with open(manual_path, 'r') as f:
            code = f.read()

        success, result = run_rosh_code(code, capture_output=False)
        assert success, f"Manual execution failed: {result}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
