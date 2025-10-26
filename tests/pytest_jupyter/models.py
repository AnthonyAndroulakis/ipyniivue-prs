"""Data models for notebook testing."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Cell:
    """Represents a code cell in the notebook."""

    code: str


@dataclass
class PyValue:
    """Result of a Python expression evaluation."""

    expr: str
    value: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class JsValue:
    """Result of a JavaScript expression evaluation."""

    expr: str
    value: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class EvaluateJs:
    """Execute JavaScript code."""

    js_code: str


@dataclass
class Value:
    """Represents a value retrieval cell."""

    python_values: list[PyValue]
    js_values: list[JsValue]


@dataclass
class Wait:
    """Represents a wait condition."""

    wait_type: str
    condition: Any
    timeout: float
