"""Tests for volume opacity synchronization."""

from pytest_jupyter import NotebookBuilder


def test_volume_opacity(page):
    """Test that changing opacity in backend syncs to frontend."""

    test = NotebookBuilder()

    test.add_cell("from ipyniivue import NiiVue", "nv = NiiVue()", "nv")

    test.wait_for_kernel_idle(idle_duration=2.0)

    test.add_cell(
        "@nv.on_image_loaded", "def update_opacity(volume):", "    volume.opacity = 0.1"
    )

    test.add_cell(
        "@nv.on_volume_updated",
        "def handle_update(volume):",
        "    if nv.volumes[0].opacity == 0.1:",
        "        print('TEST:STEP')",
    )

    test.add_cell(
        "nv.load_volumes([{'url': 'https://niivue.com/demos/images/mni152.nii.gz'}])"
    )

    test.wait_for_print("TEST:STEP")

    test.get_python_values(["nv.volumes[0].opacity"])

    test.evaluate_js("window.nv = await get_nv_ref('nv');")
    test.get_js_values(["window.nv.volumes[0].opacity"])

    test.run(page)
    print(test.python_values)
    print(test.js_values)

    assert test.python_values[0].value == 0.1
    assert test.js_values[0].value == 0.1


def test_multiple_steps(page):
    """Example showing multiple synchronization steps."""

    test = NotebookBuilder()

    test.add_cell("from ipyniivue import NiiVue", "nv = NiiVue()", "nv")

    test.add_cell(
        "@nv.on_image_loaded", "def update_opacity(volume):", "    print('TEST:STEP')"
    )

    test.add_cell(
        "@nv.on_volume_updated",
        "def handle_update(volume):",
        "    if nv.volumes[0].opacity == 0.5:",
        "        print('TEST:STEP')",
    )

    test.wait_for_kernel_idle(idle_duration=2.0)

    test.add_cell(
        "nv.load_volumes([{'url': 'https://niivue.com/demos/images/mni152.nii.gz'}])"
    )

    test.wait_for_print("TEST:STEP")

    test.get_python_values(["nv.volumes[0].opacity"])
    test.evaluate_js("window.nv = await get_nv_ref('nv');")
    test.get_js_values(["nv.volumes[0].opacity"])

    test.add_cell("nv.volumes[0].opacity = 0.5")

    test.wait_for_print("TEST:STEP")

    test.get_python_values(["nv.volumes[0].opacity"])
    test.get_js_values(["nv.volumes[0].opacity"])

    test.run(page)
    print(test.python_values)
    print(test.js_values)

    assert test.python_values[0].value == 1.0
    assert test.js_values[0].value == 1.0

    assert test.python_values[1].value == 0.5
    assert test.js_values[1].value == 0.5
