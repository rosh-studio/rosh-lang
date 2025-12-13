"""
Rosh error types
"""


class RoshError(Exception):
    """Base class for all Rosh errors"""
    pass


class RoshSyntaxError(RoshError):
    """Raised when there's a syntax error in Rosh code"""
    def __init__(self, message, line=None, column=None):
        self.line = line
        self.column = column
        location = f" at line {line}" if line else ""
        super().__init__(f"Syntax error{location}: {message}")


class RoshRuntimeError(RoshError):
    """Raised during Rosh program execution"""
    pass


class RoshTypeError(RoshRuntimeError):
    """Raised when there's a type mismatch"""
    pass


class RoshNameError(RoshRuntimeError):
    """Raised when a name is not found"""
    pass


class ReturnValue(Exception):
    """Used to return values from functions (not an error, just control flow)"""
    def __init__(self, value):
        self.value = value
        super().__init__()


class BreakLoop(Exception):
    """Used to break out of loops (not an error, just control flow)"""
    pass


class ContinueLoop(Exception):
    """Used to continue to next loop iteration (not an error, just control flow)"""
    pass


class StopExecution(Exception):
    """Used to stop program execution (not an error, just control flow)"""
    pass
