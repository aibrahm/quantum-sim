"""Quantum algorithms implementations."""

from .grover import (
    optimal_iterations,
    create_oracle,
    create_diffusion,
    grover_circuit,
    run_grover,
)

from .qft import (
    qft_circuit,
    inverse_qft_circuit,
)

from .deutsch_jozsa import (
    deutsch_jozsa_circuit,
    run_deutsch_jozsa,
)

from .teleportation import (
    teleportation_circuit,
    run_teleportation,
)

__all__ = [
    # Grover
    'optimal_iterations',
    'create_oracle',
    'create_diffusion',
    'grover_circuit',
    'run_grover',
    # QFT
    'qft_circuit',
    'inverse_qft_circuit',
    # Deutsch-Jozsa
    'deutsch_jozsa_circuit',
    'run_deutsch_jozsa',
    # Teleportation
    'teleportation_circuit',
    'run_teleportation',
]
