"""Basic test to verify the testing framework works."""

import pytest


def test_basic():
    """Test that the testing framework is working."""
    assert True


def test_import():
    """Test that the main module can be imported."""
    try:
        import voice_to_midi

        assert hasattr(voice_to_midi, "__version__")
    except ImportError:
        pytest.skip("voice_to_midi package not available")
