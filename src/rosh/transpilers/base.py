"""
Base transpiler class for all Rosh transpilers
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..ast_nodes import ASTNode, Program


class BaseTranspiler(ABC):
    """Abstract base class for all Rosh transpilers

    Provides common utilities for:
    - Code emission with indentation
    - Code accumulation
    - Comment generation
    - Meta settings (from _meta/ folder)

    Subclasses must implement:
    - transpile(): Convert Rosh AST to target language
    - validate_ast(): Validate AST contains only supported features
    """

    def __init__(self, meta: Optional[Dict[str, Any]] = None):
        self.output_lines: List[str] = []
        self.indent_level: int = 0
        self.meta: Dict[str, Any] = meta or {}

    @abstractmethod
    def transpile(self, program: Program) -> str:
        """Convert Rosh AST to target language code

        Args:
            program: Rosh Program AST node

        Returns:
            Generated code as string
        """
        pass

    @abstractmethod
    def validate_ast(self, program: Program) -> None:
        """Validate AST contains only supported features

        Raises RoshRuntimeError for unsupported constructs.

        Args:
            program: Rosh Program AST node to validate
        """
        pass

    def emit(self, code: str) -> None:
        """Emit a line of code with current indentation

        Args:
            code: Code to emit (without indentation)
        """
        indent = "    " * self.indent_level
        self.output_lines.append(f"{indent}{code}")

    def emit_blank(self) -> None:
        """Emit a blank line for readability"""
        self.output_lines.append("")

    def emit_comment(self, comment: str) -> None:
        """Emit a comment (subclass can override for language-specific syntax)

        Args:
            comment: Comment text (without comment markers)
        """
        self.emit(f"// {comment}")

    def get_code(self) -> str:
        """Get accumulated code as string

        Returns:
            All emitted code joined with newlines
        """
        return "\n".join(self.output_lines)
