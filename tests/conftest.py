"""
Pytest configuration and shared fixtures for Rosh tests
"""

import pytest
from src.rosh.lexer import Lexer
from src.rosh.parser import Parser
from src.rosh.interpreter import Interpreter


@pytest.fixture
def rosh_interpreter():
    """Create a fresh Rosh interpreter for each test"""
    return Interpreter()


@pytest.fixture
def run_rosh():
    """Fixture that returns a function to run Rosh code and capture output"""
    def _run_rosh(code, capture_output=True):
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()

        if capture_output:
            output = []
            def capture_print(value):
                output.append(str(value) if value is not None else '')
            interpreter.builtin_print = capture_print

            interpreter.run(ast)
            return output, interpreter
        else:
            interpreter.run(ast)
            return None, interpreter

    return _run_rosh


@pytest.fixture
def sample_rosh_code():
    """Sample Rosh code snippets for testing"""
    return {
        'simple': 'create number x to 42\nprint x',
        'list': 'create number nums to [1, 2, 3]\nprint nums',
        'loop': 'for i in 1 to 3 then\n    print i\nend',
        'function': 'define function double x\n    return x times 2\nend',
        'object': 'create object player\n    set name to "Hero"\nend',
    }


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "security: mark test as security-related")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "smoke: mark test as smoke test")
