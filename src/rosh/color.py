"""
Color output utilities using rich library

Provides colored and formatted output for the Rosh interpreter.
Gracefully degrades if rich is not available.
"""

import sys
from typing import Optional, TextIO

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ColorOutput:
    """Wrapper for colored output using rich"""

    def __init__(self, file: Optional[TextIO] = None):
        """Initialize color output

        Args:
            file: Output stream (default: sys.stdout)
        """
        self.file = file or sys.stdout
        if RICH_AVAILABLE:
            self.console = Console(file=self.file, force_terminal=True)
        else:
            self.console = None

    def print(self, *args, style: Optional[str] = None, **kwargs):
        """Print with optional styling

        Args:
            *args: Values to print
            style: Rich style string (e.g., "bold red", "dim", "green")
            **kwargs: Additional arguments for print/console.print
        """
        if self.console and RICH_AVAILABLE:
            self.console.print(*args, style=style, **kwargs)
        else:
            # Fallback to regular print
            print(*args, file=self.file, **kwargs)

    def success(self, message: str):
        """Print success message in green"""
        self.print(f"✓ {message}", style="bold green")

    def error(self, message: str):
        """Print error message in red"""
        self.print(f"✗ {message}", style="bold red")

    def warning(self, message: str):
        """Print warning message in yellow"""
        self.print(f"⚠ {message}", style="bold yellow")

    def info(self, message: str):
        """Print info message in blue"""
        self.print(message, style="blue")

    def dim(self, message: str):
        """Print dimmed text"""
        self.print(message, style="dim")

    def bright(self, message: str):
        """Print bright/bold text"""
        self.print(message, style="bold")

    def header(self, message: str):
        """Print header/section title"""
        self.print(f"\n{message}", style="bold cyan")

    def uuid(self, uuid_str: str):
        """Print UUID in dim style"""
        self.print(f"UUID: {uuid_str}", style="dim")

    def object_id(self, obj_id: str):
        """Print object ID in bright style"""
        self.print(f"ID: {obj_id}", style="bold yellow")

    def property_table(self, title: str, properties: dict):
        """Display properties as a formatted table

        Args:
            title: Table title
            properties: Dict of property name -> value
        """
        if self.console and RICH_AVAILABLE:
            table = Table(title=title, show_header=True, header_style="bold magenta")
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="yellow")

            for prop_name, prop_value in properties.items():
                # Format value
                if isinstance(prop_value, str):
                    formatted_value = f'"{prop_value}"'
                elif prop_value is None:
                    formatted_value = "[dim]null[/dim]"
                elif isinstance(prop_value, bool):
                    formatted_value = "[green]true[/green]" if prop_value else "[red]false[/red]"
                else:
                    formatted_value = str(prop_value)

                table.add_row(prop_name, formatted_value)

            self.console.print(table)
        else:
            # Fallback to simple formatting
            print(f"\n{title}", file=self.file)
            for prop_name, prop_value in properties.items():
                if isinstance(prop_value, str):
                    formatted_value = f'"{prop_value}"'
                else:
                    formatted_value = str(prop_value)
                print(f"  {prop_name}: {formatted_value}", file=self.file)

    def panel(self, content: str, title: Optional[str] = None, style: str = "blue"):
        """Display content in a bordered panel

        Args:
            content: Content to display
            title: Optional panel title
            style: Panel border style
        """
        if self.console and RICH_AVAILABLE:
            self.console.print(Panel(content, title=title, border_style=style))
        else:
            # Fallback to simple formatting
            if title:
                print(f"\n=== {title} ===", file=self.file)
            print(content, file=self.file)

    def syntax(self, code: str, lexer: str = "python", theme: str = "monokai"):
        """Display syntax-highlighted code

        Args:
            code: Code to highlight
            lexer: Language lexer
            theme: Color theme
        """
        if self.console and RICH_AVAILABLE:
            syntax = Syntax(code, lexer, theme=theme, line_numbers=False)
            self.console.print(syntax)
        else:
            print(code, file=self.file)

    def rule(self, title: Optional[str] = None, style: str = "dim"):
        """Print a horizontal rule with optional title

        Args:
            title: Optional rule title
            style: Rule style
        """
        if self.console and RICH_AVAILABLE:
            self.console.rule(title, style=style)
        else:
            if title:
                print(f"\n{'='*40} {title} {'='*40}", file=self.file)
            else:
                print("="*80, file=self.file)


# Global instance for easy access
_default_output = None

def get_color_output(file: Optional[TextIO] = None) -> ColorOutput:
    """Get or create the global ColorOutput instance

    Args:
        file: Output stream (default: sys.stdout)

    Returns:
        ColorOutput instance
    """
    global _default_output
    if _default_output is None or file is not None:
        _default_output = ColorOutput(file=file)
    return _default_output
