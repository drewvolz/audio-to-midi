"""Basic test to verify the testing framework works."""

import pytest


def test_basic():
    """Test that the testing framework is working."""
    assert True


def test_import():
    """Test that the main module can be imported."""
    try:
        import audio_to_midi

        assert hasattr(audio_to_midi, "__version__")
    except ImportError:
        pytest.skip("audio_to_midi package not available")
