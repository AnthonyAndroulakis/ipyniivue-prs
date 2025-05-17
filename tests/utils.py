import pytest
import re
import time
import pathlib
import json

BASE_URL = "http://127.0.0.1:8888"
LIB_FOLDER = pathlib.Path(__file__).parent.parent

def reset_notebook(path):
    """
    Reset a Jupyter notebook to its initial state.

    Parameters:
    ----------
    path : str
        Relative path to the notebook file from the notebooks directory.
    """
    full_notebook_path = LIB_FOLDER / "tests" / "notebooks" / path

    with open(full_notebook_path) as f:
        notebook_data = json.load(f)

    for cell in notebook_data['cells']:
        if cell['cell_type'] == 'code':
            cell['outputs'] = []
            cell['execution_count'] = None
    
    if 'metadata' in notebook_data:
        notebook_data['metadata'] = {'language_info': {'name': 'python'}}

    with open(full_notebook_path, 'w') as f:
        json.dump(notebook_data, f)

def wait_for_notebook_idle(page):
    """
    Wait for the Jupyter notebook kernel to become idle.

    Parameters:
    ----------
    page : playwright.sync_api.Page
        The Playwright page object.
    """
    page.wait_for_selector(r"text=/Python .* \| Idle/", timeout=10000)

def run_cells(page, path):
    """
    Execute all cells in a Jupyter notebook sequentially.

    Parameters:
    ----------
    page : playwright.sync_api.Page
        The Playwright page object.
    path : str
        Relative path to the notebook file from the notebooks directory.
    """
    full_notebook_path = LIB_FOLDER / "tests" / "notebooks" / path
    with open(full_notebook_path) as f:
        notebook_data = json.load(f)
    
    cell_count = len(notebook_data['cells'])

    for i in range(cell_count):
        page.keyboard.press('Shift+Enter')
        wait_for_notebook_idle(page)
        check_and_raise_errs(page)

def check_and_raise_errs(page):
    """
    Check the notebook for errors after cell execution and raise an exception if any are found.

    Parameters:
    ----------
    page : playwright.sync_api.Page
        The Playwright page object.
    """
    errors = page.locator('div[data-mime-type="application/vnd.jupyter.stderr"]')
    if errors.count() > 0:
        raise Exception(errors.first.inner_text())

def run_notebook(page, path):
    """
    Reset and execute a Jupyter notebook using a browser automation tool.

    Parameters:
    ----------
    page : playwright.sync_api.Page
        The Playwright page object.
    path : str
        Relative path to the notebook file from the notebooks directory.
    """
    reset_notebook(path)
    
    page.wait_for_load_state('networkidle')
    page.goto(f"{BASE_URL}/lab/tree/tests/notebooks/{path}?token=testing")

    wait_for_notebook_idle(page)

    run_cells(page, path)