#!/usr/bin/env python3
"""Tests for for loop functionality"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from io import StringIO
from rosh.lexer import Lexer
from rosh.parser import Parser
from rosh.interpreter import Interpreter


class TestForLoops(unittest.TestCase):
    """Test for loop functionality"""

    def run_code(self, code: str) -> str:
        """Helper to run Rosh code and capture output"""
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        # Capture output
        output = StringIO()
        interpreter = Interpreter(output_stream=output)
        interpreter.execute(ast)

        return output.getvalue()

    def test_basic_range_loop(self):
        """Test basic for loop: for i in 1 to 5"""
        code = """
for i in 1 to 5 then
    print i
end
"""
        output = self.run_code(code)
        lines = [line.strip() for line in output.strip().split('\n')]
        self.assertEqual(lines, ['1', '2', '3', '4', '5'])

    def test_range_with_step(self):
        """Test for loop with step: for i in 1 to 10 step 2"""
        code = """
for i in 1 to 10 step 2 then
    print i
end
"""
        output = self.run_code(code)
        lines = [line.strip() for line in output.strip().split('\n')]
        self.assertEqual(lines, ['1', '3', '5', '7', '9'])

    def test_loop_with_variable_usage(self):
        """Test for loop with variable accumulation"""
        code = """
create number total to 0
for i in 1 to 5 then
    set total to total plus i
end
print total
"""
        output = self.run_code(code)
        self.assertIn('15', output)

    def test_nested_loops(self):
        """Test nested for loops"""
        code = """
for i in 1 to 3 then
    for j in 1 to 2 then
        print i
    end
end
"""
        output = self.run_code(code)
        lines = [line.strip() for line in output.strip().split('\n')]
        # i=1 printed twice, i=2 printed twice, i=3 printed twice
        self.assertEqual(lines, ['1', '1', '2', '2', '3', '3'])

    def test_for_all_instances(self):
        """Test for loop over all instances"""
        code = """
create object item
    set name to "template"
end

clone item to apple
set apple.name to "Apple"

clone item to banana
set banana.name to "Banana"

for obj in all item then
    get obj.name
    print stack
end
"""
        output = self.run_code(code)
        # Should see template, Apple, and Banana (order may vary but should contain all)
        self.assertIn('Apple', output)
        self.assertIn('Banana', output)

    def test_empty_range(self):
        """Test for loop with no iterations"""
        code = """
print "before"
for i in 5 to 1 then
    print "should not print"
end
print "after"
"""
        output = self.run_code(code)
        self.assertIn('before', output)
        self.assertIn('after', output)
        self.assertNotIn('should not print', output)


if __name__ == '__main__':
    unittest.main()
