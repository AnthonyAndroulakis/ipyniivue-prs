"""Execute test cells in Jupyter notebook."""

import json
import uuid
from pathlib import Path

from playwright.sync_api import Page

from .evaluators import evaluate_js, evaluate_python
from .wait_handlers import handle_wait


def run_notebook_dict(page: Page, test_cells: list[dict]) -> list[dict]:
    """
    Execute test cells with explicit wait conditions.

    Parameters
    ----------
    page : Page
        Playwright page object
    test_cells : list of dict
        List of test cell dictionaries.

    Returns
    -------
    list of dict
        Returns value results
    """
    code_cells = []

    for cell_dict in test_cells:
        if cell_dict["type"] == "code":
            code_cells.append(cell_dict["code"])

    if not code_cells:
        raise ValueError("Notebook needs at least 1 code cell.")

    load_notebook(page, code_cells)

    results = []

    for cell_dict in test_cells:
        cell_type = cell_dict["type"]

        if cell_type == "code":
            page.keyboard.press("Shift+Enter")

        elif cell_type == "value":
            value_result = {}

            if "python" in cell_dict:
                value_result["python"] = evaluate_python(page, cell_dict["python"])

            if "js" in cell_dict:
                value_result["js"] = evaluate_js(page, cell_dict["js"])

            if value_result:
                results.append(value_result)

        elif cell_type == "wait":
            handle_wait(page, cell_dict)

        elif cell_type == "evaluate":
            page.evaluate(f"async () => {{ {cell_dict['js_code']} }}")

    return results


def load_notebook(
    page: Page, cells: list[str], notebook_name: str = "test_notebook.ipynb"
):
    """
    Create a notebook with given cells and load it in the browser.

    Parameters
    ----------
    page : Page
        Playwright page object
    cells : list of str
        List of code strings, one per cell
    notebook_name : str
        Name for the notebook file
    """
    notebook_path = page.temp_notebook_dir / notebook_name
    create_notebook(cells, notebook_path)

    notebook_url = f"{page.jupyter_server}/lab/tree/{notebook_name}"
    page.goto(notebook_url)
    page.wait_for_load_state("networkidle")


def create_notebook(cells: list[str], notebook_path: Path):
    """
    Create a Jupyter notebook from a list of code cells.

    Parameters
    ----------
    cells : list of str
        List of code strings, one per cell
    notebook_path : Path
        Where to save the notebook
    """
    notebook = {
        "cells": [],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.9.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    for code in cells:
        lines = code.split("\n")
        source_lines = [
            line + "\n" if i < len(lines) - 1 else line for i, line in enumerate(lines)
        ]

        notebook["cells"].append(
            {
                "cell_type": "code",
                "execution_count": None,
                "id": str(uuid.uuid4()),
                "metadata": {},
                "outputs": [],
                "source": source_lines,
            }
        )

    with open(notebook_path, "w") as f:
        json.dump(notebook, f)
