"""
Rosh Spec Audit Tool

Verify that implementations comply with the language specification.

SPEC CHAIN:
    This tool verifies:
    1. CLI commands (rosh-cli.toml) → cli.py, runtime JS
    2. Console commands (rosh-console.toml) → ALL emitters (phaser, pygame, threejs)

    See: docs/SPEC-CHAIN.md

Usage:
    python -m rosh.spec.audit              # Audit all implementations
    python -m rosh.spec.audit --js         # Audit JS files only
    python -m rosh.spec.audit --python     # Audit Python files only
    python -m rosh.spec.audit --console    # Audit emitter console parity

WARNING: Rosh is experimental. This implementation may change.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

from .loader import SpecLoader, CommandSpec


class AuditResult:
    """Result of an audit check."""

    def __init__(self, target: str, layer: str = None, spec_type: str = "cli"):
        self.target = target
        self.layer = layer
        self.spec_type = spec_type  # "cli" or "console"
        self.missing: List[str] = []
        self.found: List[str] = []
        self.errors: List[str] = []

    @property
    def ok(self) -> bool:
        return len(self.missing) == 0 and len(self.errors) == 0

    def __str__(self) -> str:
        if self.ok:
            return f"OK: {self.target} ({len(self.found)} commands)"
        else:
            missing_str = ", ".join(self.missing[:10])
            if len(self.missing) > 10:
                missing_str += f" (+{len(self.missing) - 10} more)"
            return f"FAIL: {self.target} - missing: {missing_str}"


class Auditor:
    """Audit implementations against specs."""

    def __init__(self):
        self.loader = SpecLoader()
        self.console_loader = SpecLoader()

        # Load specs
        try:
            self.loader.load("cli")
        except FileNotFoundError:
            pass
        try:
            self.console_loader.load("console")
        except FileNotFoundError:
            pass

        self.base_path = Path(__file__).parent.parent.parent.parent

    def audit_js_file(self, filepath: Path, layer: str = None) -> AuditResult:
        """Audit a JavaScript file for command compliance."""
        result = AuditResult(str(filepath.relative_to(self.base_path)), layer)

        if not filepath.exists():
            result.errors.append(f"File not found: {filepath}")
            return result

        content = filepath.read_text()

        # Get commands to check
        if layer:
            commands = self.loader.get_commands_by_layer(layer)
        else:
            commands = self.loader.get_all_commands()

        # Check each command
        for name, cmd in commands.items():
            found = False
            for cmd_name in cmd.all_names:
                # Look for parts[0] === 'name' pattern
                pattern = rf"parts\[0\] === '{cmd_name}'"
                if re.search(pattern, content):
                    found = True
                    break

            if found:
                result.found.append(name)
            else:
                result.missing.append(name)

        return result

    def audit_python_file(self, filepath: Path, layer: str = None) -> AuditResult:
        """Audit a Python file for command compliance."""
        result = AuditResult(str(filepath.relative_to(self.base_path)), layer)

        if not filepath.exists():
            result.errors.append(f"File not found: {filepath}")
            return result

        content = filepath.read_text()

        # Get commands to check
        if layer:
            commands = self.loader.get_commands_by_layer(layer)
        else:
            commands = self.loader.get_all_commands()

        # Check each command - look for command handling patterns
        for name, cmd in commands.items():
            found = False
            for cmd_name in cmd.all_names:
                # Look for various patterns in Python
                patterns = [
                    rf"'{cmd_name}'",  # String literal
                    rf'"{cmd_name}"',  # Double-quoted string
                    rf"== '{cmd_name}'",  # Equality check
                    rf'== "{cmd_name}"',
                    rf"in \[.*'{cmd_name}'",  # In list
                    rf"in \(.*'{cmd_name}'",  # In tuple
                ]
                for pattern in patterns:
                    if re.search(pattern, content):
                        found = True
                        break
                if found:
                    break

            if found:
                result.found.append(name)
            else:
                result.missing.append(name)

        return result

    def audit_emitter_console(self, filepath: Path) -> AuditResult:
        """Audit an emitter for console command compliance.

        SPEC CHAIN: rosh-console.toml → emitters/*.py
        """
        result = AuditResult(
            str(filepath.relative_to(self.base_path)),
            spec_type="console"
        )

        if not filepath.exists():
            result.errors.append(f"File not found: {filepath}")
            return result

        content = filepath.read_text()

        # Get console commands from spec
        console_commands = self.console_loader.get_all_commands()

        for name, cmd in console_commands.items():
            # Only check required commands
            # The spec uses a different structure - check for 'required' key
            spec_data = self.console_loader._cache.get("console", {})
            cmd_data = spec_data.get("commands", {}).get(name, {})
            is_required = cmd_data.get("required", False)

            if not is_required:
                continue

            # Look for command handling in the emitter
            found = False
            for cmd_name in cmd.all_names:
                # Emitters use patterns like:
                # self.write("if command in ('list', 'ls', 'objects'):")
                # self.write("elif command == 'set':")
                patterns = [
                    rf"'{cmd_name}'",
                    rf'"{cmd_name}"',
                    rf"command == '{cmd_name}'",
                    rf"command in \(.*'{cmd_name}'",
                    rf"command in \[.*'{cmd_name}'",
                ]
                for pattern in patterns:
                    if re.search(pattern, content):
                        found = True
                        break
                if found:
                    break

            if found:
                result.found.append(name)
            else:
                result.missing.append(name)

        return result

    def audit_all_emitter_consoles(self) -> List[AuditResult]:
        """Audit all emitters for console command parity.

        SPEC CHAIN: rosh-console.toml → phaser.py, pygame.py, threejs.py
        All emitters MUST implement ALL required console commands.
        """
        results = []
        emitters_dir = self.base_path / "src" / "rosh" / "emitters"

        for emitter_name in ["phaser.py", "pygame.py", "threejs.py"]:
            filepath = emitters_dir / emitter_name
            if filepath.exists():
                results.append(self.audit_emitter_console(filepath))
            else:
                result = AuditResult(f"emitters/{emitter_name}", spec_type="console")
                result.errors.append(f"Emitter not found: {filepath}")
                results.append(result)

        return results

    def audit_all(self) -> List[AuditResult]:
        """Audit all known implementations."""
        results = []

        # JS files
        runtime_dir = self.base_path / "src" / "rosh" / "runtime"

        # rosh-core.js - core layer only
        core_result = self.audit_js_file(runtime_dir / "rosh-core.js", layer="core")
        if not core_result.errors or "not found" not in str(core_result.errors):
            results.append(core_result)

        # rosh-3d.js - 3d layer only
        result_3d = self.audit_js_file(runtime_dir / "rosh-3d.js", layer="3d")
        if not result_3d.errors or "not found" not in str(result_3d.errors):
            results.append(result_3d)

        # rosh-runtime.js - all commands (standalone)
        runtime_result = self.audit_js_file(runtime_dir / "rosh-runtime.js", layer=None)
        if not runtime_result.errors or "not found" not in str(runtime_result.errors):
            results.append(runtime_result)

        # Python CLI
        results.append(self.audit_python_file(
            self.base_path / "src" / "rosh" / "cli.py",
            layer=None
        ))

        # Emitter console commands
        results.extend(self.audit_all_emitter_consoles())

        return results


def main():
    """Run the audit."""
    import argparse

    parser = argparse.ArgumentParser(description="Audit Rosh implementations")
    parser.add_argument("--js", action="store_true", help="Audit JS files only")
    parser.add_argument("--python", action="store_true", help="Audit Python files only")
    parser.add_argument("--console", action="store_true", help="Audit emitter console parity only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
    args = parser.parse_args()

    auditor = Auditor()

    # Get results based on filter
    if args.console:
        results = auditor.audit_all_emitter_consoles()
    else:
        results = auditor.audit_all()

        # Filter if requested
        if args.js:
            results = [r for r in results if r.target.endswith(".js")]
        elif args.python:
            results = [r for r in results if r.target.endswith(".py")]

    # Print results
    print()
    print("Rosh Spec Audit")
    print("=" * 60)

    # Group by spec type
    cli_results = [r for r in results if r.spec_type == "cli"]
    console_results = [r for r in results if r.spec_type == "console"]

    all_ok = True

    if cli_results:
        print()
        print("CLI Commands (rosh-cli.toml)")
        print("-" * 40)
        for result in cli_results:
            if result.ok:
                print(f"  OK  {result.target}")
                if args.verbose:
                    print(f"       {len(result.found)} commands found")
            else:
                all_ok = False
                print(f" FAIL {result.target}")
                if result.missing:
                    print(f"       Missing: {', '.join(result.missing)}")
                if result.errors:
                    print(f"       Errors: {', '.join(result.errors)}")

    if console_results:
        print()
        print("Console Commands (rosh-console.toml)")
        print("-" * 40)
        for result in console_results:
            if result.ok:
                print(f"  OK  {result.target}")
                if args.verbose:
                    print(f"       {len(result.found)} commands found")
            else:
                all_ok = False
                print(f" FAIL {result.target}")
                if result.missing:
                    print(f"       Missing: {', '.join(result.missing)}")
                if result.errors:
                    print(f"       Errors: {', '.join(result.errors)}")

        # Check parity across emitters
        if len(console_results) > 1:
            found_sets = [set(r.found) for r in console_results if r.ok]
            if found_sets:
                all_found = set.intersection(*found_sets)
                any_found = set.union(*found_sets)
                parity_issues = any_found - all_found
                if parity_issues:
                    print()
                    print("  PARITY WARNING: Not all emitters implement:")
                    for cmd in sorted(parity_issues):
                        emitters_with = [r.target.split('/')[-1] for r in console_results if cmd in r.found]
                        print(f"    - {cmd} (only in: {', '.join(emitters_with)})")
                    all_ok = False

    print()
    print("=" * 60)

    if all_ok:
        print("All implementations comply with spec.")
        print()
        print("Spec chain verified:")
        print("  rosh-cli.toml → cli.py")
        print("  rosh-console.toml → phaser.py, pygame.py, threejs.py")
        return 0
    else:
        print("Some implementations are out of sync with spec.")
        print()
        print("See: docs/SPEC-CHAIN.md for dependency documentation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
