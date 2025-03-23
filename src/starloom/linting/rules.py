"""Custom ruff rules for starloom."""

from typing import List

from .ruff_types import LinterContext, Rule, RuleSet, Import, ImportFrom


def check_src_imports(
    node: Import | ImportFrom,
    context: LinterContext,
) -> List[Rule]:
    """Check for imports from src directory."""
    if isinstance(node, ImportFrom):
        if node.module and node.module.startswith("src."):
            return [
                Rule(
                    "src-import",
                    node.range,
                    "Do not import from 'src' directory. Use the package name directly.",
                )
            ]
    return []


def register_rules() -> RuleSet:
    """Register custom rules."""
    return RuleSet(
        name="starloom",
        rules=[
            Rule(
                name="src-import",
                check=check_src_imports,
                message="Do not import from 'src' directory. Use the package name directly.",
            ),
        ],
    )
