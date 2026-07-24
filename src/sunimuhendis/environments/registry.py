"""Environment registry — instantiate evaluation environments by name.

Each environment is built by a factory that imports its (possibly heavy)
simulator dependencies *lazily*, so ``import sunimuhendis`` and
``list_environments()`` stay dependency-free. A given environment's deps are
only imported when you actually ``make_env(<name>)`` — which is what makes the
per-environment install extras (e.g. ``sunimuhendis[heat_exchanger]``) meaningful.
"""
from typing import Callable, Dict, List, Any
from ..core.base_environment import BaseEnvironment


def _make_heat_exchanger(**kwargs) -> BaseEnvironment:
    from .heat_exchanger.env import HeatExchangerEnv
    from .heat_exchanger.simulator import HeatExchangerSimulator
    from .heat_exchanger.score import get_score_function
    
    score_version = kwargs.get("score_version", "heat_exchanger_score_v1")
    score_fn = get_score_function(score_version)
    
    return HeatExchangerEnv(HeatExchangerSimulator(), score_fn)


_REGISTRY: Dict[str, Callable[..., BaseEnvironment]] = {
    "heat_exchanger": _make_heat_exchanger,
}


def list_environments() -> List[str]:
    """Return the names of all registered environments."""
    return sorted(_REGISTRY)


def make_env(name: str, **kwargs) -> BaseEnvironment:
    """Instantiate a registered environment by name.

    Raises KeyError if the name is unknown, listing the available options.
    """
    try:
        factory = _REGISTRY[name]
    except KeyError:
        raise KeyError(
            "Unknown environment {!r}. Available: {}".format(name, list_environments())
        ) from None
    return factory(**kwargs)
