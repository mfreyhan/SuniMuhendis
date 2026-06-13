import pytest

def test_imports():
    try:
        import ht
        import fluids
        import CoolProp
        import numpy as np
        import scipy
    except ImportError as e:
        pytest.fail(f"Required package not found: {e}")
