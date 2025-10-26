"""Python and JavaScript value evaluation."""

import ast

from playwright.sync_api import Page


def evaluate_python(page: Page, expressions: list[str]) -> list:
    """
    Evaluate Python expressions in kernel.

    Parameters
    ----------
    page : Page
        Playwright page object
    expressions : list of str
        Python expressions to evaluate

    Returns
    -------
    list
        Results for each expression
    """
    results = []
    for expr in expressions:
        try:
            value = get_python_value(page, expr)
            results.append(value)
            print(f"  Python: {expr} = {value}")
        except Exception as e:
            results.append({"error": str(e)})
            print(f"  Python: {expr} = Error: {e}")
    return results


def evaluate_js(page: Page, expressions: list[tuple]) -> list:
    """
    Evaluate JavaScript expressions.

    Parameters
    ----------
    page : Page
        Playwright page object
    expressions : list of str
        List of js_expr strings

    Returns
    -------
    list
        Results for each expression
    """
    results = []
    for js_expr in expressions:
        try:
            value = get_js_value(page, js_expr)
            results.append(value)
            print(f"  JS: {js_expr} = {value}")
        except Exception as e:
            results.append({"error": str(e)})
            print(f"  JS: {js_expr} = Error: {e}")

    return results


def get_python_value(page: Page, code: str):
    """
    Execute Python code and get the result.

    Parameters
    ----------
    page : Page
        Playwright page object
    code : str
        Python code to execute

    Returns
    -------
    Any
        The result
    """
    result = page.evaluate(f"""
        async () => {{
            const result = await window.kernel.exec("{code}");
            return result;
        }}
    """)

    if "error" in result:
        return result
    try:
        return ast.literal_eval(result["output"])
    except:  # noqa: E722
        return result["output"]


def get_js_value(page: Page, js_expression: str):
    """
    Execute JavaScript and return the result.

    Parameters
    ----------
    page : Page
        Playwright page object
    js_expression : str
        JavaScript expression to evaluate

    Returns
    -------
    Any
        The result of the JavaScript expression
    """
    return page.evaluate(f"""
        async () => {{
            return {js_expression};
        }}
    """)
