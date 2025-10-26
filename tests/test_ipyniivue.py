"""Basic tests for ipyniivue."""


def test_it_loads():
    """Test that ipyniivue can be imported."""
    import ipyniivue

    assert ipyniivue.__version__ is not None
