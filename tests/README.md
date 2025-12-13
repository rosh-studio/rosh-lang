# Rosh Test Suite

Comprehensive test suite for the Rosh programming language.

## Test Organization

### Unit Tests

**`test_list_iteration.py`** - List iteration feature (v0.0.5)
- Tests `for item in list then` syntax
- Covers empty lists, mixed types, nested iteration
- Tests break/continue within list loops
- 12 test cases

**`test_string_methods.py`** - String manipulation (v0.0.5)
- Split: 5 test cases
- Substring: 5 test cases
- Case conversion (lowercase/uppercase): 6 test cases
- Trim: 5 test cases
- indexOf/lastIndexOf: 8 test cases
- Combined operations: 3 test cases
- **Total: 32 test cases**

**`test_remote_import_smoke.py`** - Remote import security
- Tests user confirmation flow
- Tests acceptance/rejection handling
- Verifies security warnings
- Tests local vs remote detection
- Error handling for network issues
- **Total: 15 test cases**

### Integration Tests

**`test_manual_extracts.py`** - ROSH-MANUAL.rosh validation
- Extracts and tests code examples from manual
- Ensures manual stays in sync with implementation
- Tests all major features through manual examples
- Includes full manual execution test

## Running Tests

### Run all tests
```bash
pytest tests/

# With verbose output
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/rosh
```

### Run specific test file
```bash
pytest tests/test_list_iteration.py -v
pytest tests/test_string_methods.py -v
pytest tests/test_remote_import_smoke.py -v
```

### Run specific test class or function
```bash
# Run all tests in a class
pytest tests/test_string_methods.py::TestStringSplit -v

# Run a specific test
pytest tests/test_list_iteration.py::TestListIteration::test_iterate_number_list -v
```

### Run tests by marker
```bash
# Run slow tests
pytest tests/ -v -m slow

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Run with different verbosity levels
```bash
pytest tests/ -v          # Verbose
pytest tests/ -vv         # Very verbose
pytest tests/ -q          # Quiet
pytest tests/ --tb=short  # Short traceback
```

## Test Structure

Each test file follows this pattern:

```python
import pytest
from src.rosh.lexer import Lexer
from src.rosh.parser import Parser
from src.rosh.interpreter import Interpreter

def run_rosh(code):
    """Helper to run Rosh code and capture output"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    interpreter = Interpreter()

    # Capture print output
    output = []
    def capture_print(value):
        output.append(str(value) if value is not None else '')
    interpreter.builtin_print = capture_print

    interpreter.run(ast)
    return output, interpreter

class TestFeature:
    def test_case(self):
        code = """
        create number x to 42
        print x
        """
        output, _ = run_rosh(code)
        assert output == ['42']
```

## Adding New Tests

### 1. Unit Tests for New Features

When adding a new feature:

1. Create a new test file: `test_<feature_name>.py`
2. Import necessary modules
3. Create test classes grouping related tests
4. Write focused tests for each aspect of the feature
5. Include edge cases and error conditions

Example:
```python
class TestNewFeature:
    def test_basic_usage(self):
        """Test the basic happy path"""
        # ...

    def test_edge_case(self):
        """Test boundary conditions"""
        # ...

    def test_error_handling(self):
        """Test error cases"""
        # ...
```

### 2. Integration Tests

When updating ROSH-MANUAL.rosh:

1. Add examples demonstrating the feature
2. Run `pytest tests/test_manual_extracts.py`
3. If needed, add specific test cases to `test_manual_extracts.py`

### 3. Smoke Tests

For critical security or user-facing flows:

1. Create smoke tests that verify the flow works end-to-end
2. Use mocking for external dependencies (network, filesystem)
3. Focus on user experience, not implementation details

## Coverage Goals

- **Core language features**: 90%+ coverage
- **Standard library**: 80%+ coverage
- **Error handling**: 100% of error paths tested
- **Security features**: 100% coverage + smoke tests

## Test Categories

### Fast Tests (default)
Unit tests that run quickly (<100ms each)
```bash
pytest tests/
```

### Slow Tests
Integration tests that take longer (marked with `@pytest.mark.slow`)
```bash
pytest tests/ -m slow
```

### Security Tests
Tests for security-critical features
```bash
pytest tests/test_remote_import_smoke.py
```

## Continuous Integration

Tests should:
- ✅ Run on every commit
- ✅ Pass before merging PRs
- ✅ Include linting (ruff, black)
- ✅ Measure code coverage
- ✅ Test on Python 3.10, 3.11, 3.12

## Test Data

Test data files can be placed in `tests/fixtures/`:
```
tests/
  fixtures/
    sample.rosh
    test-data.json
    modules/
      test-module.rosh
```

## Debugging Tests

### Run with debugger
```bash
pytest tests/test_file.py --pdb
```

### Show print statements
```bash
pytest tests/ -v -s
```

### Run last failed tests
```bash
pytest tests/ --lf
```

### See which tests would run
```bash
pytest tests/ --collect-only
```

## Performance Testing

For performance-critical features, add benchmarks:

```python
import time

def test_performance():
    start = time.time()
    # Run operation
    duration = time.time() - start
    assert duration < 1.0  # Should complete in under 1 second
```

## Future Test Additions

### Planned for v0.0.6
- [ ] Type checking function tests
- [ ] String interpolation tests
- [ ] List slicing tests
- [ ] Modulo operator tests

### Planned for v0.0.7
- [ ] Try/catch error handling tests
- [ ] Regular expression tests
- [ ] String replace tests

### Planned for v0.0.8
- [ ] Package manifest parser tests
- [ ] Dependency resolution tests
- [ ] Package verification tests

### Planned for v0.0.9
- [ ] Multi-user security tests
- [ ] Sandboxing tests
- [ ] Permission system tests

## Contributing

When contributing tests:

1. Follow existing test patterns
2. Write clear test names that describe what's being tested
3. Include docstrings explaining the test purpose
4. Test both success and failure cases
5. Keep tests independent (no shared state)
6. Use descriptive assertion messages
7. Run the full test suite before submitting

## Resources

- **pytest documentation**: https://docs.pytest.org/
- **Python testing best practices**: https://realpython.com/pytest-python-testing/
- **Mocking guide**: https://docs.python.org/3/library/unittest.mock.html
