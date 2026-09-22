"""Small, explicit physics adapters around the pinned NASA backend.

The pinned NASA Carter class returns radians while the solver consumes degrees,
and its default arguments collapse to zero deviation.  This implementation is
the algebraic form documented by NASA, evaluated on the solver's span grid.
"""

from typing import Any


class CorrectedCarterDeviation:
    """Carter deviation for axial compressor rows, returned in degrees."""

    model_id = "carter_mattingly_corrected_v1"

    @staticmethod
    def _on_grid(values: Any, target):
        import numpy as np

        source = np.asarray(values, dtype=float).reshape(-1)
        if source.size == 1:
            return np.full_like(target, source.item(), dtype=float)
        return np.interp(target, np.linspace(0.0, 1.0, source.size), source)

    def __call__(self, row, upstream):  # noqa: ARG002 - NASA loss API
        import numpy as np

        span = np.asarray(row.percent_hub_shroud, dtype=float)
        inlet_deg = self._on_grid(row.metal_inlet_angle, span)
        exit_deg = self._on_grid(row.metal_exit_angle, span)
        solidity = self._on_grid(row.solidity, span)
        solidity = np.maximum(solidity, 1e-9)

        # NASA documents gamma_e = (4*alpha_e*sqrt(sigma)-gamma_i) /
        # (4*sqrt(sigma)-1).  Solving for alpha_e gives this deviation.
        return (inlet_deg - exit_deg) / (4.0 * np.sqrt(solidity))


class SeededLossAdapter:
    """Supply a finite pre-solve seed before a state-dependent loss is usable."""

    def __init__(self, delegate, initial_loss=0.05):
        self.delegate = delegate
        self.initial_loss = initial_loss
        self._loss_type = delegate._loss_type

    @property
    def LossType(self):
        return self._loss_type

    @property
    def loss_type(self):
        return self._loss_type

    def _needs_seed(self, row):
        import numpy as np

        mach = row.M_rel if getattr(row.row_type, "name", "") == "Rotor" else row.M
        return not np.any(np.asarray(mach, dtype=float) > 1e-8)

    def __call__(self, row, upstream):
        import numpy as np

        if self._needs_seed(row):
            return np.full_like(row.r, self.initial_loss, dtype=float)
        return self.delegate(row, upstream)


class MeanlineGeometryLossAdapter(SeededLossAdapter):
    """Run a NASA mean-line correlation with scalar mean blade geometry.

    NASA's Kacker-Okapuu implementation accepts spanwise flow state but casts
    pitch/chord and trailing-edge geometry to ``float``.  Recent spool geometry
    setup expands those values to arrays, so the unadapted correlation fails for
    more than one streamline.  The correlation is mean-line by construction;
    this adapter supplies its expected scalar geometry and restores the row.
    """

    def __call__(self, row, upstream):
        import numpy as np

        # TurbineSpool asks the loss model for an initialization value before
        # the row exit Mach, density and temperature exist.  Supply a seed only
        # for that pre-solve call; subsequent iterations evaluate the delegate.
        if self._needs_seed(row):
            return np.full_like(row.r, 0.05, dtype=float)

        saved_pitch_to_chord = row._pitch_to_chord
        saved_stagger = row._stagger
        try:
            row._pitch_to_chord = float(np.asarray(saved_pitch_to_chord).mean())
            row._stagger = float(np.asarray(saved_stagger).mean())
            return self.delegate(row, upstream)
        finally:
            row._pitch_to_chord = saved_pitch_to_chord
            row._stagger = saved_stagger
