import pytest
import pathlib
from utils import run_notebook

NOTEBOOK_DIR = pathlib.Path(__file__).parent / "notebooks"

NOTEBOOKS = list(NOTEBOOK_DIR.glob("test_*.ipynb"))

@pytest.mark.parametrize("path", NOTEBOOKS, ids=[p.name for p in NOTEBOOKS])
def test_notebooks(path, page):
    run_notebook(page, path)