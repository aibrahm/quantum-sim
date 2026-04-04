"""Grover's search algorithm."""

import numpy as np
from typing import List, Optional, Callable, Tuple
from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import run_circuit, get_statevector, ExecutionResult
from ..core.state_vector import StateVector


def optimal_iterations(n_qubits: int, n_marked: int = 1) -> int:
    """Optimal iteration count: floor(pi/4 * sqrt(N/M))."""
    N = 2 ** n_qubits
    M = n_marked
    return int(np.floor(np.pi / 4 * np.sqrt(N / M)))


def create_oracle(n_qubits: int, marked_states: List[int]) -> QuantumCircuit:
    """Create a phase oracle that flips marked states."""
    oracle = QuantumCircuit(n_qubits, name="oracle")

    for marked in marked_states:
        # Apply X gates to qubits that should be |0⟩ for this marked state
        bits = [(marked >> i) & 1 for i in range(n_qubits)]

        for i, bit in enumerate(bits):
            if bit == 0:
                oracle.x(i)

        # Multi-controlled Z gate (phase flip on |11...1⟩)
        if n_qubits == 1:
            oracle.z(0)
        elif n_qubits == 2:
            oracle.cz(0, 1)
        elif n_qubits == 3:
            # CCZ using Toffoli and ancilla-free decomposition
            oracle.h(2)
            oracle.ccx(0, 1, 2)
            oracle.h(2)
        else:
            # For more qubits, use multi-controlled Z decomposition
            # This is a simplified version - full implementation would use
            # proper multi-controlled gate decomposition
            oracle.h(n_qubits - 1)
            for i in range(n_qubits - 2):
                oracle.ccx(i, i + 1, n_qubits - 1)
            oracle.h(n_qubits - 1)

        # Undo X gates
        for i, bit in enumerate(bits):
            if bit == 0:
                oracle.x(i)

    return oracle


def create_diffusion(n_qubits: int) -> QuantumCircuit:
    """Diffusion operator D = 2|s><s| - I."""
    diffusion = QuantumCircuit(n_qubits, name="diffusion")

    # Apply H gates
    for i in range(n_qubits):
        diffusion.h(i)

    # Apply X gates
    for i in range(n_qubits):
        diffusion.x(i)

    # Multi-controlled Z (marks |11...1⟩ which is |00...0⟩ after X gates)
    if n_qubits == 1:
        diffusion.z(0)
    elif n_qubits == 2:
        diffusion.cz(0, 1)
    elif n_qubits == 3:
        diffusion.h(2)
        diffusion.ccx(0, 1, 2)
        diffusion.h(2)
    else:
        diffusion.h(n_qubits - 1)
        for i in range(n_qubits - 2):
            diffusion.ccx(i, i + 1, n_qubits - 1)
        diffusion.h(n_qubits - 1)

    # Apply X gates
    for i in range(n_qubits):
        diffusion.x(i)

    # Apply H gates
    for i in range(n_qubits):
        diffusion.h(i)

    return diffusion


def grover_circuit(
    n_qubits: int,
    marked_states: List[int],
    iterations: Optional[int] = None
) -> QuantumCircuit:
    """Build a complete Grover search circuit."""
    if iterations is None:
        iterations = optimal_iterations(n_qubits, len(marked_states))

    qc = QuantumCircuit(n_qubits, name="grover")

    # Initial superposition
    for i in range(n_qubits):
        qc.h(i)

    # Grover iterations
    oracle = create_oracle(n_qubits, marked_states)
    diffusion = create_diffusion(n_qubits)

    for _ in range(iterations):
        # Oracle
        qc.compose(oracle)
        # Diffusion
        qc.compose(diffusion)

    return qc


def run_grover(
    n_qubits: int,
    marked_states: List[int],
    iterations: Optional[int] = None,
    shots: int = 1024
) -> Tuple[ExecutionResult, float]:
    """Run Grover's algorithm, returning (result, success_probability)."""
    if iterations is None:
        iterations = optimal_iterations(n_qubits, len(marked_states))

    # Build and run circuit
    qc = grover_circuit(n_qubits, marked_states, iterations)
    qc.measure_all()

    result = run_circuit(qc, shots=shots)

    # Calculate success probability
    total_marked_counts = sum(
        result.counts.get(format(m, f'0{n_qubits}b'), 0)
        for m in marked_states
    )
    success_prob = total_marked_counts / shots

    return result, success_prob


def grover_with_custom_oracle(
    n_qubits: int,
    oracle_fn: Callable[[QuantumCircuit], QuantumCircuit],
    iterations: Optional[int] = None,
    n_marked: int = 1,
    shots: int = 1024
) -> ExecutionResult:
    """Run Grover with a custom oracle function."""
    if iterations is None:
        iterations = optimal_iterations(n_qubits, n_marked)

    qc = QuantumCircuit(n_qubits, name="grover_custom")

    # Initial superposition
    for i in range(n_qubits):
        qc.h(i)

    # Grover iterations
    diffusion = create_diffusion(n_qubits)

    for _ in range(iterations):
        # Apply custom oracle
        qc = oracle_fn(qc)
        # Diffusion
        qc.compose(diffusion)

    qc.measure_all()
    return run_circuit(qc, shots=shots)
