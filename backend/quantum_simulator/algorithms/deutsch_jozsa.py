"""
Deutsch-Jozsa Algorithm Implementation.
Determines if a function is constant or balanced in a single query.
"""

from typing import Literal
from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import run_circuit


def deutsch_jozsa_circuit(
    n_qubits: int,
    oracle_type: Literal["constant_0", "constant_1", "balanced"]
) -> QuantumCircuit:
    """
    Create Deutsch-Jozsa circuit with specified oracle.

    Args:
        n_qubits: Number of input qubits (total circuit has n+1 qubits)
        oracle_type: Type of oracle function
            - "constant_0": f(x) = 0 for all x
            - "constant_1": f(x) = 1 for all x
            - "balanced": f(x) = 0 for half inputs, 1 for other half

    Returns:
        Complete Deutsch-Jozsa circuit
    """
    # Total qubits: n input + 1 ancilla
    total_qubits = n_qubits + 1
    qc = QuantumCircuit(total_qubits, name="deutsch_jozsa")

    # Initialize ancilla qubit to |1⟩
    qc.x(n_qubits)

    # Apply Hadamard to all qubits
    for i in range(total_qubits):
        qc.h(i)

    # Apply oracle
    if oracle_type == "constant_0":
        # f(x) = 0: do nothing (identity)
        pass
    elif oracle_type == "constant_1":
        # f(x) = 1: flip ancilla
        qc.x(n_qubits)
    elif oracle_type == "balanced":
        # f(x) = x_0 XOR x_1 XOR ... (balanced function)
        # CNOT from each input qubit to ancilla
        for i in range(n_qubits):
            qc.cx(i, n_qubits)

    # Apply Hadamard to input qubits (not ancilla)
    for i in range(n_qubits):
        qc.h(i)

    return qc


def run_deutsch_jozsa(
    n_qubits: int,
    oracle_type: Literal["constant_0", "constant_1", "balanced"],
    shots: int = 1024
) -> dict:
    """
    Run Deutsch-Jozsa algorithm.

    Args:
        n_qubits: Number of input qubits
        oracle_type: Type of oracle
        shots: Number of measurement shots

    Returns:
        Dictionary with results including detected function type
    """
    qc = deutsch_jozsa_circuit(n_qubits, oracle_type)

    # Measure only input qubits (not ancilla)
    for i in range(n_qubits):
        qc.measure(i, i)

    result = run_circuit(qc, shots=shots)

    # Analyze results
    # If all zeros -> constant, otherwise -> balanced
    all_zeros = "0" * n_qubits
    zero_count = result.counts.get(all_zeros, 0)

    # Determine result
    is_constant = zero_count > shots * 0.9  # Allow some noise tolerance
    detected_type = "constant" if is_constant else "balanced"

    actual_type = "constant" if oracle_type.startswith("constant") else "balanced"
    correct = detected_type == actual_type

    return {
        "oracle_type": oracle_type,
        "detected_type": detected_type,
        "correct": correct,
        "counts": result.counts,
        "shots": shots,
        "zero_probability": zero_count / shots,
    }


__all__ = [
    'deutsch_jozsa_circuit',
    'run_deutsch_jozsa',
]
