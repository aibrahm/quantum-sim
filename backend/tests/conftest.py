"""Shared pytest fixtures."""

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def seed_rng():
    """Seed numpy's RNG before every test so measurement-based tests are reproducible."""
    np.random.seed(1234)
