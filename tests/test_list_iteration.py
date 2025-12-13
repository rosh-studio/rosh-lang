"""
Unit tests for list iteration (v0.0.5)

Tests the 'for item in list then' syntax added in v0.0.5
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


class TestListIteration:
    """Test for item in list iteration"""

    def test_iterate_number_list(self):
        """Iterate through a list of numbers"""
        code = """
        create number nums to [1, 2, 3]
        for num in nums then
            print num
        end
        """
        output, _ = run_rosh(code)
        assert output == ['1', '2', '3']

    def test_iterate_string_list(self):
        """Iterate through a list of strings"""
        code = """
        create string names to ["Alice", "Bob", "Charlie"]
        for name in names then
            print name
        end
        """
        output, _ = run_rosh(code)
        assert output == ['Alice', 'Bob', 'Charlie']

    def test_iterate_empty_list(self):
        """Iterate through an empty list (should produce no output)"""
        code = """
        create number empty to []
        for item in empty then
            print item
        end
        print "done"
        """
        output, _ = run_rosh(code)
        assert output == ['done']

    def test_iterate_mixed_list(self):
        """Iterate through a list with mixed types"""
        code = """
        create number mixed to [1, "two", 3]
        for item in mixed then
            print item
        end
        """
        output, _ = run_rosh(code)
        assert output == ['1', 'two', '3']

    def test_iterate_with_conditional(self):
        """Use conditional logic inside list iteration"""
        code = """
        create number scores to [85, 92, 78, 95, 88]
        for score in scores then
            if score is above 90 then
                print "A"
            end
        end
        """
        output, _ = run_rosh(code)
        assert output == ['A', 'A']

    def test_iterate_and_accumulate(self):
        """Accumulate values while iterating"""
        code = """
        create number sum to 0
        create number nums to [10, 20, 30]
        for num in nums then
            set sum to sum plus num
        end
        print sum
        """
        output, _ = run_rosh(code)
        assert output == ['60']

    def test_iterate_nested_list(self):
        """Iterate through list containing lists"""
        code = """
        create number pairs to [[1, 2], [3, 4]]
        for pair in pairs then
            print pair
        end
        """
        output, _ = run_rosh(code)
        assert output == ['[1, 2]', '[3, 4]']

    def test_iterate_list_from_expression(self):
        """Iterate through a list created from an expression"""
        code = """
        create number base to [1, 2, 3]
        for item in base then
            print item
        end
        """
        output, _ = run_rosh(code)
        assert output == ['1', '2', '3']

    def test_iterate_with_break(self):
        """Test break inside list iteration"""
        code = """
        create number nums to [1, 2, 3, 4, 5]
        for num in nums then
            if num is equal to 3 then
                break
            end
            print num
        end
        """
        output, _ = run_rosh(code)
        assert output == ['1', '2']

    def test_iterate_with_continue(self):
        """Test continue inside list iteration"""
        code = """
        create number nums to [1, 2, 3, 4, 5]
        for num in nums then
            if num is equal to 3 then
                continue
            end
            print num
        end
        """
        output, _ = run_rosh(code)
        assert output == ['1', '2', '4', '5']

    def test_iterate_single_item_list(self):
        """Iterate through a list with a single item"""
        code = """
        create number single to [42]
        for item in single then
            print item
        end
        """
        output, _ = run_rosh(code)
        assert output == ['42']

    def test_nested_list_iteration(self):
        """Test nested list iteration"""
        code = """
        create number outer to [1, 2]
        for i in outer then
            create number inner to [10, 20]
            for j in inner then
                create number product to i times j
                print product
            end
        end
        """
        output, _ = run_rosh(code)
        assert output == ['10', '20', '20', '40']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
