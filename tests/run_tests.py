#!/usr/bin/env python3
"""
Rosh Test Runner

Runs all tests in the test suite.

Usage:
    python tests/run_tests.py          # Run all tests
    python tests/run_tests.py -v       # Verbose output
    python tests/run_tests.py TestName # Run specific test
"""
import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def run_tests():
    """Discover and run all tests"""
    # Discover tests in the tests directory
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Run tests with appropriate verbosity
    verbosity = 2 if '-v' in sys.argv or '--verbose' in sys.argv else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == '__main__':
    print("🧪 Running Rosh Test Suite\n")
    run_tests()
