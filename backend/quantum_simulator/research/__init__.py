"""
Research paper implementations.

Contains implementations of cutting-edge quantum computing research,
with full attribution to original authors.
"""

from .qsvt import (
    QSPAngles,
    BlockEncoding,
    qsp_sequence,
    qsvt_circuit,
    qsvt_apply,
    qsvt_matrix_inversion,
    qsvt_search,
    qsvt_phase_estimation,
    demonstrate_qsvt_unification,
)

__all__ = [
    'QSPAngles',
    'BlockEncoding',
    'qsp_sequence',
    'qsvt_circuit',
    'qsvt_apply',
    'qsvt_matrix_inversion',
    'qsvt_search',
    'qsvt_phase_estimation',
    'demonstrate_qsvt_unification',
]
