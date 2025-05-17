# tests/conftest.py

import pytest
import subprocess
import time
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="session")
def jupyter_server():
    cmd = [
        'jupyter', 'lab',
        '--no-browser',
        '--NotebookApp.token="testing"',
        '--port=8888',
        '--ip=127.0.0.1',
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)
    yield "http://127.0.0.1:8888"
    proc.terminate()
    proc.wait()

@pytest.fixture(scope="session")
def page(jupyter_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            base_url=jupyter_server
        )
        page = context.new_page()
        yield page
        browser.close()
