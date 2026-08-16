import pytest

from sphinx_bioschemas import profiles, validation


@pytest.fixture(autouse=True)
def _reset_bioschemas_validation_caches():
    profiles.reset_caches()
    validation.reset_caches()
    yield
    profiles.reset_caches()
    validation.reset_caches()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Any accidental network call fails loudly instead of hanging on an egress-less box."""

    def _forbidden(*args, **kwargs):
        raise AssertionError("network access attempted in tests")

    monkeypatch.setattr(profiles, "_urlopen", _forbidden)
