"""Fluent API for building notebook tests."""

from typing import Callable, Union

from .models import Cell, EvaluateJs, JsValue, PyValue, Value, Wait
from .runner import run_notebook_dict


class NotebookBuilder:
    """
    Builder for creating and executing test notebooks.
    """

    def __init__(self):
        self.entries: list[Union[Cell, Value, Wait]] = []

    def add_cell(self, *code: str):
        """
        Add a code cell to the notebook.

        Parameters
        ----------
        *code : str
            Python code line(s) for the cell.
        """
        cell_code = "\n".join(code)
        self.entries.append(Cell(code=cell_code))
        return self

    def wait_for_kernel_idle(self, idle_duration: float = 1.0, timeout: float = 10.0):
        """
        Wait for kernel to be idle for sustained period.

        Parameters
        ----------
        idle_duration : float
            How long kernel must stay idle (seconds)
        timeout : float
            Maximum time to wait (seconds)
        """
        self.entries.append(
            Wait(
                wait_type="kernel_idle",
                condition=idle_duration,
                timeout=timeout,
            )
        )
        return self

    def wait_for_kernel_message(
        self, filter_func: Callable[[dict], bool], timeout: float = 10.0
    ):
        """
        Wait for specific kernel message matching filter.

        Parameters
        ----------
        filter_func : callable
            Function that takes message dict and returns True when condition is met.
            Message dict has keys: 'direction', 'message', 'timestamp'
        timeout : float
            Maximum time to wait
        """
        self.entries.append(
            Wait(
                wait_type="kernel_message",
                condition=filter_func,
                timeout=timeout,
            )
        )
        return self

    def wait_for_print(self, text, timeout: float = 10.0):
        self.wait_for_kernel_message(
            lambda msg: (
                msg.get("direction") == "in"
                and msg.get("message", {}).get("header", {}).get("msg_type") == "stream"
                and text
                == msg.get("message", {}).get("content", {}).get("text", "").strip()
            ),
            timeout,
        )

    def wait_for_time(self, milliseconds: int):
        """
        Wait for fixed amount of time.

        Parameters
        ----------
        milliseconds : int
            Time to wait in milliseconds
        """
        self.entries.append(
            Wait(
                wait_type="time",
                condition=milliseconds,
                timeout=milliseconds / 1000.0 + 1.0,
            )
        )
        return self

    def wait_for_selector(self, selector: str, timeout: float = 10.0):
        """
        Wait for page selector to appear.

        Parameters
        ----------
        selector : str
            CSS selector to wait for
        timeout : float
            Maximum time to wait
        """
        self.entries.append(
            Wait(
                wait_type="selector",
                condition=selector,
                timeout=timeout,
            )
        )
        return self

    def get_python_values(self, expressions: list[str]):
        """
        Evaluate Python expressions and store results.

        Parameters
        ----------
        expressions : list of str
            Python expressions to evaluate
        """
        python_values = [PyValue(expr=expr) for expr in expressions]
        self.entries.append(Value(python_values=python_values, js_values=[]))
        return self

    def get_js_values(self, expressions: list[str]):
        """
        Evaluate JavaScript expressions and store results.

        Parameters
        ----------
        expressions : list of str
            Either:
            - List of JS expressions
        """
        js_values = []

        for expr in expressions:
            js_values.append(JsValue(expr=expr))

        self.entries.append(Value(python_values=[], js_values=js_values))
        return self

    def evaluate_js(self, js_code: str):
        self.entries.append(EvaluateJs(js_code=js_code))
        self.wait_for_time(100)

    def as_dict(self) -> list[dict]:
        """
        Convert to (list of) dict.

        Returns
        -------
        list of dict
            Test cells in the format expected by run_notebook_dict
        """
        test_cells = []

        for entry in self.entries:
            if isinstance(entry, Cell):
                test_cells.append({"type": "code", "code": entry.code})
            elif isinstance(entry, Value):
                value_cell = {"type": "value"}

                if entry.python_values:
                    value_cell["python"] = [pv.expr for pv in entry.python_values]

                if entry.js_values:
                    value_cell["js"] = [jv.expr for jv in entry.js_values]

                test_cells.append(value_cell)
            elif isinstance(entry, Wait):
                test_cells.append(
                    {
                        "type": "wait",
                        "wait_type": entry.wait_type,
                        "condition": entry.condition,
                        "timeout": entry.timeout,
                    }
                )
            elif isinstance(entry, EvaluateJs):
                test_cells.append({"type": "evaluate", "js_code": entry.js_code})

        return test_cells

    def run(self, page):
        """
        Execute the notebook and populate results.

        Parameters
        ----------
        page : Page
            Playwright page object
        """
        test_cells = self.as_dict()
        results = run_notebook_dict(page, test_cells)
        self._populate_results(results)

    def _populate_results(self, results: list[dict]):
        """Populate value fields from execution results."""
        result_idx = 0
        for entry in self.entries:
            if isinstance(entry, Value):
                if result_idx < len(results):
                    result = results[result_idx]

                    if "python" in result:
                        for i, value in enumerate(result["python"]):
                            if i < len(entry.python_values):
                                if isinstance(value, dict) and "error" in value:
                                    entry.python_values[i].error = value["error"]
                                else:
                                    entry.python_values[i].value = value

                    if "js" in result:
                        for i, value in enumerate(result["js"]):
                            if i < len(entry.js_values):
                                if isinstance(value, dict) and "error" in value:
                                    entry.js_values[i].error = value["error"]
                                else:
                                    entry.js_values[i].value = value

                    result_idx += 1

    @property
    def python_values(self) -> list[PyValue]:
        """Get all Python values from all value cells."""
        values = []
        for entry in self.entries:
            if isinstance(entry, Value):
                values.extend(entry.python_values)
        return values

    @property
    def js_values(self) -> list[JsValue]:
        """Get all JS values from all value cells."""
        values = []
        for entry in self.entries:
            if isinstance(entry, Value):
                values.extend(entry.js_values)
        return values
