import pytest
import subprocess
import threading

from playwright.sync_api import sync_playwright

@pytest.fixture(scope="session")
def jupyter_server():
    cmd = [
        'jupyter', 'lab',
        '--no-browser',
        '--ServerApp.token=testing',
        '--port=8888',
        '--ip=127.0.0.1',
    ]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )

    server_ready = threading.Event()

    def read_output():
        for line in proc.stdout:
            #print(line, flush=True)
            if "http://127.0.0.1" in line:
                server_ready.set()

    t = threading.Thread(target=read_output)
    t.daemon = True
    t.start()

    max_timeout = 15.0
    if not server_ready.wait(timeout=max_timeout):
        proc.terminate()
        proc.wait()
        raise RuntimeError("Failed to start Jupyter server within timeout.")

    yield "http://127.0.0.1:8888" #technically not entirely correct, since what if there's already another jupyter server running...

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

def pytest_addoption(parser):
    parser.addoption("--ipynb", action="store_true",
                     default=False, help="Include Jupyter notebook tests")

def pytest_collection_modifyitems(config, items):
    if config.getoption("--ipynb"):
        '''
        try:
            subprocess.run(['playwright', 'install'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while installing Playwright browsers: {e}")
        '''
        return
    skip_notebooks = pytest.mark.skip(reason="Jupyter notebook tests skipped by default, use --ipynb to run.")
    for item in items:
        if "test_notebooks.py" in str(item.fspath):
            item.add_marker(skip_notebooks)