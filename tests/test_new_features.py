#!/usr/bin/env python3
"""Tests for new language features: negatives, boolean ops, returns"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from io import StringIO
from rosh.lexer import Lexer
from rosh.parser import Parser
from rosh.interpreter import Interpreter


class TestNewFeatures(unittest.TestCase):
    """Test new language features"""

    def run_code(self, code: str) -> str:
        """Helper to run Rosh code and capture output"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        output = StringIO()
        interpreter = Interpreter(output_stream=output)
        interpreter.execute(ast)

        return output.getvalue()

    # Negative Numbers Tests
    def test_negative_literal(self):
        """Test negative number literals"""
        code = """
create number x to -5
print x
"""
        output = self.run_code(code)
        self.assertIn('-5', output)

    def test_negative_in_expression(self):
        """Test negative numbers in expressions"""
        code = """
create number y to 10 plus -3
print y
"""
        output = self.run_code(code)
        self.assertIn('7', output)

    def test_double_negative(self):
        """Test double negative"""
        code = """
create number z to - -7
print z
"""
        output = self.run_code(code)
        self.assertIn('7', output)

    # Boolean Operators Tests
    def test_and_operator(self):
        """Test AND operator"""
        code = """
create number x to 7
if x is above 5 and x is below 10 then
    print "yes"
end
"""
        output = self.run_code(code)
        self.assertIn('yes', output)

    def test_or_operator(self):
        """Test OR operator"""
        code = """
create number y to 3
if y is below 5 or y is above 10 then
    print "yes"
end
"""
        output = self.run_code(code)
        self.assertIn('yes', output)

    def test_not_operator(self):
        """Test NOT operator"""
        code = """
create number z to 15
if not z is below 10 then
    print "yes"
end
"""
        output = self.run_code(code)
        self.assertIn('yes', output)

    def test_complex_boolean(self):
        """Test complex boolean expression"""
        code = """
create number a to 25
create number b to 85
if a is above 18 and b is above 80 or a is below 12 then
    print "qualified"
end
"""
        output = self.run_code(code)
        self.assertIn('qualified', output)

    # Function Return Values Tests
    def test_simple_return(self):
        """Test simple function return"""
        code = """
define function double x
    create number result to x times 2
    return result
end

call double 5
print
"""
        output = self.run_code(code)
        self.assertIn('10', output)

    def test_return_expression(self):
        """Test return with expression"""
        code = """
define function sum a b
    return a plus b
end

call sum 10 20
print
"""
        output = self.run_code(code)
        self.assertIn('30', output)

    def test_early_return(self):
        """Test early return in function"""
        code = """
define function check_positive x
    if x is below 0 then
        return false
    end
    return true
end

call check_positive -5
print
"""
        output = self.run_code(code)
        self.assertIn('false', output)

    def test_return_no_value(self):
        """Test return without value"""
        code = """
define function no_return
    return
end

call no_return
"""
        output = self.run_code(code)
        # Should not error, just return None
        self.assertIsNotNone(output)

    # List/Array Tests
    def test_list_literal(self):
        """Test list literal creation"""
        code = """
create number nums to [1, 2, 3]
print nums
"""
        output = self.run_code(code)
        self.assertIn('[1, 2, 3]', output)

    def test_list_access(self):
        """Test list element access"""
        code = """
create number nums to [10, 20, 30]
get nums[1]
print
"""
        output = self.run_code(code)
        self.assertIn('20', output)

    def test_list_modify(self):
        """Test list element modification"""
        code = """
create number nums to [1, 2, 3]
set nums[1] to 99
print nums
"""
        output = self.run_code(code)
        self.assertIn('[1, 99, 3]', output)

    def test_empty_list(self):
        """Test empty list"""
        code = """
create number empty to []
print empty
"""
        output = self.run_code(code)
        self.assertIn('[]', output)

    # Break/Continue Tests
    def test_break_for_loop(self):
        """Test break in for loop"""
        code = """
for i in 1 to 10 then
    if i is equal to 5 then
        break
    end
    print i
end
"""
        output = self.run_code(code)
        self.assertIn('4', output)
        self.assertNotIn('5', output)

    def test_continue_for_loop(self):
        """Test continue in for loop"""
        code = """
for i in 1 to 5 then
    if i is equal to 3 then
        continue
    end
    print i
end
"""
        output = self.run_code(code)
        self.assertIn('2', output)
        self.assertNotIn('3', output)
        self.assertIn('4', output)


if __name__ == '__main__':
    unittest.main()
