"""
Base Emitter for IR → Target Code Translation

All emitters inherit from this and implement target-specific code generation.
Emitters are "mechanical translators" - they don't make semantic decisions.

See: rosh-dev/proposals/ROSH-IR-SPECIFICATION.md
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..ir import (
    IR_Program, IR_Object, IR_Event, IR_Action, IR_Function,
    IR_Value, IR_Expression, IR_Conditional, IR_Loop, IR_Metadata,
    denormalize_coordinate
)


class BaseEmitter(ABC):
    """Abstract base class for all target emitters.

    Subclasses must implement:
    - emit_object(obj: IR_Object) -> str
    - emit_event(event: IR_Event) -> str
    - emit_action(action: IR_Action) -> str
    - emit_expression(expr: IR_Expression) -> str
    """

    def __init__(self, ir: IR_Program, meta: Dict[str, Any] = None):
        """Initialize emitter with IR program.

        Args:
            ir: The IR_Program to emit code for
            meta: Optional target-specific metadata from _meta/*.toml
        """
        self.ir = ir
        self.meta = meta or {}

        # Code generation state
        self.output: List[str] = []
        self.indent_level = 0
        self.indent_str = "    "  # 4 spaces
        self.capability_manifest: Dict[str, Any] = {
            "schema_version": 1,
            "capabilities": []
        }

    # =========================================================================
    # Public API
    # =========================================================================

    @abstractmethod
    def emit(self) -> str:
        """Generate target code from IR.

        Returns:
            Complete target code as string
        """
        pass

    # =========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    def emit_object(self, obj: IR_Object) -> str:
        """Generate code for an object definition."""
        pass

    @abstractmethod
    def emit_event(self, event: IR_Event) -> str:
        """Generate code for an event handler."""
        pass

    @abstractmethod
    def emit_action(self, action: IR_Action) -> str:
        """Generate code for an action."""
        pass

    @abstractmethod
    def emit_expression(self, expr: IR_Expression) -> str:
        """Generate code for an expression."""
        pass

    # =========================================================================
    # Coordinate Helpers
    # =========================================================================

    def to_target_x(self, ir_x: float) -> float:
        """Convert normalized X to target coordinates.

        Default: top-left origin, pixel units.
        Override for center-origin or unit-based systems.
        """
        target_width = self.meta.get('canvas', {}).get('width', self.ir.metadata.canvas_width)
        origin = self.meta.get('origin', 'top-left')
        return denormalize_coordinate(ir_x, target_width, origin)

    def to_target_y(self, ir_y: float) -> float:
        """Convert normalized Y to target coordinates.

        Default: top-left origin, pixel units.
        Override for center-origin or unit-based systems.
        """
        target_height = self.meta.get('canvas', {}).get('height', self.ir.metadata.canvas_height)
        origin = self.meta.get('origin', 'top-left')
        return denormalize_coordinate(ir_y, target_height, origin)

    def to_target_width(self, ir_width: float) -> float:
        """Convert normalized width to target units."""
        target_width = self.meta.get('canvas', {}).get('width', self.ir.metadata.canvas_width)
        return ir_width * target_width

    def to_target_height(self, ir_height: float) -> float:
        """Convert normalized height to target units."""
        target_height = self.meta.get('canvas', {}).get('height', self.ir.metadata.canvas_height)
        return ir_height * target_height

    # =========================================================================
    # Code Generation Helpers
    # =========================================================================

    def write(self, line: str):
        """Write a line of code with current indentation."""
        indent = self.indent_str * self.indent_level
        self.output.append(f"{indent}{line}")

    def write_blank(self):
        """Write a blank line."""
        self.output.append("")

    def write_comment(self, text: str):
        """Write a comment (subclass should override for target syntax)."""
        self.write(f"// {text}")

    def get_code(self) -> str:
        """Get all generated code as a single string."""
        return "\n".join(self.output)

    def indent(self):
        """Increase indentation level."""
        self.indent_level += 1

    def dedent(self):
        """Decrease indentation level."""
        self.indent_level = max(0, self.indent_level - 1)

    # =========================================================================
    # IR Value Helpers
    # =========================================================================

    def get_value(self, ir_value: IR_Value, context: str = None) -> Any:
        """Extract raw value from IR_Value, with optional context-aware conversion.

        Args:
            ir_value: The IR_Value to extract
            context: Optional context ('x', 'y', 'width', 'height', 'color')

        Returns:
            The value in target-appropriate form
        """
        if ir_value.type == 'percentage':
            if context in ('x', 'width'):
                return self.to_target_x(ir_value.value)
            elif context in ('y', 'height'):
                return self.to_target_y(ir_value.value)
            else:
                return ir_value.value

        elif ir_value.type == 'color':
            return ir_value.value  # Already hex integer

        elif ir_value.type == 'expression':
            return self.emit_expression(ir_value.value)

        else:
            return ir_value.value

    def format_color(self, color_value: int) -> str:
        """Format color value for target (default: hex format)."""
        return f"0x{color_value:06x}"

    # =========================================================================
    # Control Flow Helpers
    # =========================================================================

    def emit_conditional(self, cond: IR_Conditional) -> str:
        """Generate code for conditional (if/else).

        Default implementation for C-like languages.
        Override for different syntax.
        """
        lines = []
        lines.append(f"if ({self.emit_expression(cond.condition)}) {{")

        for action in cond.then_actions:
            if action:
                lines.append(f"    {self.emit_action(action)}")

        if cond.else_actions:
            lines.append("} else {")
            for action in cond.else_actions:
                if action:
                    lines.append(f"    {self.emit_action(action)}")

        lines.append("}")
        return "\n".join(lines)

    def emit_loop(self, loop: IR_Loop) -> str:
        """Generate code for loop.

        Default implementation for C-like languages.
        Override for different syntax.
        """
        lines = []

        if loop.type == 'while':
            lines.append(f"while ({self.emit_expression(loop.condition)}) {{")
        elif loop.type == 'for':
            start = self.emit_expression(loop.start)
            end = self.emit_expression(loop.end)
            step = self.emit_expression(loop.step) if loop.step else "1"
            lines.append(f"for (let {loop.iterator} = {start}; {loop.iterator} <= {end}; {loop.iterator} += {step}) {{")
        elif loop.type == 'for_each':
            iterable = self.emit_expression(loop.iterable)
            lines.append(f"for (const {loop.iterator} of {iterable}) {{")

        for action in loop.body:
            if action:
                lines.append(f"    {self.emit_action(action)}")

        lines.append("}")
        return "\n".join(lines)
