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
    qft_on_register,
    inverse_qft_on_register,
)

from .deutsch_jozsa import (
    deutsch_jozsa_circuit,
    run_deutsch_jozsa,
)

from .teleportation import (
    teleportation_circuit,
    run_teleportation,
)

from .qpe import (
    qpe_circuit,
    run_qpe,
    qpe_for_hamiltonian,
)

from .vqe import (
    PauliTerm,
    PauliHamiltonian,
    hardware_efficient_ansatz,
    uccsd_ansatz,
    run_vqe,
    run_h2_vqe,
    VQEResult,
)

from .qaoa import (
    QAOAProblem,
    QAOAResult,
    qaoa_circuit,
    run_qaoa,
    run_maxcut_qaoa,
)

from .qec import (
    QECResult,
    run_bit_flip_code,
    run_phase_flip_code,
    run_shor_code,
    compare_codes,
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
    'qft_on_register',
    'inverse_qft_on_register',
    # Deutsch-Jozsa
    'deutsch_jozsa_circuit',
    'run_deutsch_jozsa',
    # Teleportation
    'teleportation_circuit',
    'run_teleportation',
    # QPE
    'qpe_circuit',
    'run_qpe',
    'qpe_for_hamiltonian',
    # VQE
    'PauliTerm',
    'PauliHamiltonian',
    'hardware_efficient_ansatz',
    'uccsd_ansatz',
    'run_vqe',
    'run_h2_vqe',
    'VQEResult',
    # QAOA
    'QAOAProblem',
    'QAOAResult',
    'qaoa_circuit',
    'run_qaoa',
    'run_maxcut_qaoa',
    # QEC
    'QECResult',
    'run_bit_flip_code',
    'run_phase_flip_code',
    'run_shor_code',
    'compare_codes',
]
