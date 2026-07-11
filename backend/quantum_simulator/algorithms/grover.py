"""Grover's search algorithm."""

import numpy as np
from typing import List, Optional, Callable, Tuple
from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import run_circuit, ExecutionResult


def optimal_iterations(n_qubits: int, n_marked: int = 1) -> int:
    """Optimal iteration count: floor(pi/4 * sqrt(N/M))."""
    N = 2 ** n_qubits
    M = n_marked
    return int(np.floor(np.pi / 4 * np.sqrt(N / M)))


def _mcp(qc: QuantumCircuit, theta: float, controls: List[int], target: int) -> None:
    """Multi-controlled phase gate, decomposed recursively without ancillas."""
    if not controls:
        qc.p(theta, target)
    elif len(controls) == 1:
        qc.cp(theta, controls[0], target)
    else:
        qc.cp(theta / 2, controls[-1], target)
        _mcx(qc, controls[:-1], controls[-1])
        qc.cp(-theta / 2, controls[-1], target)
        _mcx(qc, controls[:-1], controls[-1])
        _mcp(qc, theta / 2, controls[:-1], target)


def _mcx(qc: QuantumCircuit, controls: List[int], target: int) -> None:
    """Multi-controlled X gate via H-conjugated multi-controlled phase."""
    if not controls:
        qc.x(target)
    elif len(controls) == 1:
        qc.cx(controls[0], target)
    elif len(controls) == 2:
        qc.ccx(controls[0], controls[1], target)
    else:
        qc.h(target)
        _mcp(qc, np.pi, controls, target)
        qc.h(target)


def _mcz(qc: QuantumCircuit, qubits: List[int]) -> None:
    """Multi-controlled Z: phase flip on |11...1> over the given qubits."""
    if len(qubits) == 1:
        qc.z(qubits[0])
    else:
        _mcp(qc, np.pi, qubits[:-1], qubits[-1])


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
        _mcz(oracle, list(range(n_qubits)))

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
    _mcz(diffusion, list(range(n_qubits)))

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
