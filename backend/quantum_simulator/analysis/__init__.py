"""Analysis and metrics tools."""

from .circuit_stats import (
    gate_count,
    two_qubit_gate_count,
    three_qubit_gate_count,
    circuit_depth,
    critical_path,
    qubit_utilization,
    parameter_count,
    circuit_summary,
)

from .entanglement import (
    schmidt_decomposition,
    von_neumann_entropy,
    entanglement_entropy,
    concurrence,
    concurrence_mixed,
    negativity,
    mutual_information,
    entanglement_spectrum,
    pairwise_entanglement,
    full_entanglement_analysis,
)

__all__ = [
    # Circuit stats
    'gate_count',
    'two_qubit_gate_count',
    'three_qubit_gate_count',
    'circuit_depth',
    'critical_path',
    'qubit_utilization',
    'parameter_count',
    'circuit_summary',
    # Entanglement
    'schmidt_decomposition',
    'von_neumann_entropy',
    'entanglement_entropy',
    'concurrence',
    'concurrence_mixed',
    'negativity',
    'mutual_information',
    'entanglement_spectrum',
    'pairwise_entanglement',
    'full_entanglement_analysis',
]
