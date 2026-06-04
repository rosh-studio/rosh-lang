"""Validation helpers for AI-generated Rosh."""

from __future__ import annotations

from dataclasses import dataclass

from rosh_lang.core.model import ExtensionCommandStatement, Programme
from rosh_lang.core.parser import parse_string


@dataclass(frozen=True, slots=True)
class ValidationResult:
    programme: Programme | None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.programme is not None and not self.error


def validate_generated_rosh(source: str) -> ValidationResult:
    text = source.strip()
    if not text:
        return ValidationResult(programme=None, error="Planner returned no Rosh code.")
    try:
        programme = parse_string(text, source="<intent>", strict_blocks=True)
    except Exception as exc:
        return ValidationResult(programme=None, error=str(exc))

    for stmt in programme.statements:
        if isinstance(stmt, ExtensionCommandStatement):
            return ValidationResult(
                programme=None,
                error=f"Planner returned unsupported extension command: {stmt.verb}",
            )
    return ValidationResult(programme=programme)
