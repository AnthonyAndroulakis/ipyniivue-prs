"""Wait condition handlers."""

import time
from datetime import datetime

from playwright.sync_api import Page

kernel_status = "idle"
last_status_change = datetime.now()

_message_callbacks = []


def register_callback(callback):
    """Register a message callback."""
    _message_callbacks.append(callback)
    return callback


def unregister_callback(callback):
    """Unregister a message callback."""
    if callback in _message_callbacks:
        _message_callbacks.remove(callback)


def clear_callbacks():
    """Clear all callbacks."""
    _message_callbacks.clear()


def handle_wait(page: Page, wait_cell: dict):
    """
    Route to appropriate wait handler.

    Parameters
    ----------
    page : Page
        Playwright page object
    wait_cell : dict
        Wait cell dictionary with wait_type, condition, timeout
    """
    wait_type = wait_cell["wait_type"]
    condition = wait_cell["condition"]
    timeout = wait_cell["timeout"]

    handlers = {
        "kernel_idle": wait_kernel_idle,
        "kernel_message": wait_kernel_message,
        "time": wait_time,
        "selector": wait_selector,
    }

    handler = handlers.get(wait_type)
    if not handler:
        raise ValueError(f"Unknown wait type: {wait_type}")

    handler(page, condition, timeout)


def wait_kernel_idle(page: Page, idle_duration: float, timeout: float):
    """
    Wait for kernel to be idle.

    Parameters
    ----------
    page : Page
        Playwright page object
    idle_duration : float
        How long the kernel must stay idle in seconds
    timeout : float
        Maximum time to wait in seconds
    """
    global kernel_status, last_status_change

    start_time = time.time()
    while time.time() - start_time < timeout:
        if kernel_status == "idle":
            time_since_last_change = (
                datetime.now() - last_status_change
            ).total_seconds()
            if time_since_last_change >= idle_duration:
                return
        page.wait_for_timeout(100)

    raise TimeoutError(f"Kernel did not become idle within {timeout} seconds.")


def wait_kernel_message(page: Page, filter_func, timeout: float):
    """
    Wait for a kernel message matching the filter function.

    Parameters
    ----------
    page : Page
        Playwright page object
    filter_func : callable
        Function that takes message dict and returns True when condition is met
    timeout : float
        Maximum time to wait in seconds
    """
    matched = [False]

    def callback(payload):
        if filter_func(payload):
            matched[0] = True
            return True
        return False

    register_callback(callback)

    try:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if matched[0]:
                return
            page.wait_for_timeout(100)
        raise TimeoutError(f"No kernel message matched filter within {timeout} seconds")
    finally:
        unregister_callback(callback)


def wait_time(page: Page, milliseconds: int, timeout: float):
    """
    Wait for fixed time.

    Parameters
    ----------
    page : Page
        Playwright page object
    milliseconds : int
        Time to wait in milliseconds
    """
    page.wait_for_timeout(milliseconds)


def wait_selector(page: Page, selector: str, timeout: float):
    """
    Wait for DOM selector to appear.

    Parameters
    ----------
    page : Page
        Playwright page object
    selector : str
        CSS selector to wait for
    timeout : float
        Maximum time to wait in seconds
    """
    page.wait_for_selector(selector, timeout=timeout * 1000)


def update_kernel_status(payload):
    """
    Update global kernel status from message payload.

    Parameters
    ----------
    payload : dict
        Message payload with direction, message, timestamp
    """
    global kernel_status, last_status_change

    for callback in _message_callbacks:
        try:
            callback(payload)
        except:  # noqa: E722
            pass

    direction = payload["direction"]
    msg = payload.get("message", {})
    msg_type = msg.get("header", {}).get("msg_type", "")

    if direction == "in" and msg_type == "status":
        execution_state = msg.get("content", {}).get("execution_state")
        if execution_state and execution_state != kernel_status:
            kernel_status = execution_state
            last_status_change = datetime.now()
