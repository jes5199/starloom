from typing import Protocol, Any

class LinterContext(Protocol):
    """Type stub for ruff.linter.LinterContext"""
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class Rule(Protocol):
    """Type stub for ruff.rules.Rule"""
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class RuleSet(Protocol):
    """Type stub for ruff.rules.RuleSet"""
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class Import(Protocol):
    """Type stub for ruff.tree.Import"""
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class ImportFrom(Protocol):
    """Type stub for ruff.tree.ImportFrom"""
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
