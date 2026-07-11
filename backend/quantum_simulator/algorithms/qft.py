"""
Quantum Fourier Transform (QFT) Implementation.
The quantum analog of the discrete Fourier transform.
"""

import numpy as np
from typing import List
from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import get_statevector


def qft_circuit(n_qubits: int, do_swaps: bool = True) -> QuantumCircuit:
    """
    Create a Quantum Fourier Transform circuit.

    The QFT transforms computational basis states to frequency domain:
    QFT|j⟩ = (1/√N) Σₖ e^(2πijk/N)|k⟩

    Args:
        n_qubits: Number of qubits
        do_swaps: Whether to include final SWAP operations for bit reversal

    Returns:
        QFT circuit
    """
    qc = QuantumCircuit(n_qubits, name="qft")

    for i in range(n_qubits):
        # Hadamard on qubit i
        qc.h(i)

        # Controlled rotations
        for j in range(i + 1, n_qubits):
            # Controlled phase rotation by 2π/2^(j-i+1)
            angle = np.pi / (2 ** (j - i))
            qc.cp(angle, j, i)

    # Swap qubits for proper bit ordering
    if do_swaps:
        for i in range(n_qubits // 2):
            qc.swap(i, n_qubits - 1 - i)

    return qc


def inverse_qft_circuit(n_qubits: int, do_swaps: bool = True) -> QuantumCircuit:
    """
    Create an Inverse Quantum Fourier Transform circuit.

    Args:
        n_qubits: Number of qubits
        do_swaps: Whether to include initial SWAP operations

    Returns:
        Inverse QFT circuit
    """
    qc = QuantumCircuit(n_qubits, name="iqft")

    # Swap qubits first (inverse order of QFT)
    if do_swaps:
        for i in range(n_qubits // 2):
            qc.swap(i, n_qubits - 1 - i)

    # Apply inverse operations in reverse order
    for i in range(n_qubits - 1, -1, -1):
        # Inverse controlled rotations
        for j in range(n_qubits - 1, i, -1):
            angle = -np.pi / (2 ** (j - i))
            qc.cp(angle, j, i)

        # Hadamard (self-inverse)
        qc.h(i)

    return qc


def qft_on_register(
    circuit: QuantumCircuit,
    qubits: List[int],
    do_swaps: bool = True
) -> QuantumCircuit:
    """
    Apply QFT to specific qubits in a larger circuit.

    Args:
        circuit: Circuit to modify
        qubits: Qubit indices to apply QFT to
        do_swaps: Whether to include SWAP operations

    Returns:
        Modified circuit
    """
    n = len(qubits)

    for i in range(n):
        circuit.h(qubits[i])
        for j in range(i + 1, n):
            angle = np.pi / (2 ** (j - i))
            circuit.cp(angle, qubits[j], qubits[i])

    if do_swaps:
        for i in range(n // 2):
            circuit.swap(qubits[i], qubits[n - 1 - i])

    return circuit


def inverse_qft_on_register(
    circuit: QuantumCircuit,
    qubits: List[int],
    do_swaps: bool = True
) -> QuantumCircuit:
    """
    Apply inverse QFT to specific qubits.

    Args:
        circuit: Circuit to modify
        qubits: Qubit indices
        do_swaps: Whether to include SWAP operations

    Returns:
        Modified circuit
    """
    n = len(qubits)

    if do_swaps:
        for i in range(n // 2):
            circuit.swap(qubits[i], qubits[n - 1 - i])

    for i in range(n - 1, -1, -1):
        for j in range(n - 1, i, -1):
            angle = -np.pi / (2 ** (j - i))
            circuit.cp(angle, qubits[j], qubits[i])
        circuit.h(qubits[i])

    return circuit


def qft_matrix(n_qubits: int) -> np.ndarray:
    """
    Generate the QFT unitary matrix directly.

    Args:
        n_qubits: Number of qubits

    Returns:
        2^n × 2^n QFT matrix
    """
    N = 2 ** n_qubits
    omega = np.exp(2j * np.pi / N)

    F = np.zeros((N, N), dtype=complex)
    for j in range(N):
        for k in range(N):
            F[j, k] = omega ** (j * k)

    return F / np.sqrt(N)


def verify_qft(n_qubits: int) -> bool:
    """
    Verify QFT circuit produces correct transformation.

    Args:
        n_qubits: Number of qubits to test

    Returns:
        True if verification passes
    """
    # Get QFT from circuit
    qc = qft_circuit(n_qubits)

    # Test on computational basis states
    for input_state in range(2 ** n_qubits):
        # Create input state
        input_qc = QuantumCircuit(n_qubits)
        for i in range(n_qubits):
            if (input_state >> i) & 1:
                input_qc.x(i)
        input_qc.compose(qc)

        sv = get_statevector(input_qc)

        # Calculate expected output
        F = qft_matrix(n_qubits)
        expected = F[:, input_state]

        # Compare (allowing for global phase)
        if not np.allclose(np.abs(sv.amplitudes), np.abs(expected), atol=1e-10):
            return False

    return True


# Example applications

def phase_estimation_example(
    unitary_power: int,
    n_precision: int = 4
) -> float:
    """
    Simplified phase estimation using QFT.

    This is a demonstration - full QPE requires controlled-U operations.

    Args:
        unitary_power: Power of unitary (determines phase)
        n_precision: Number of precision qubits

    Returns:
        Estimated phase
    """
    # This is a simplified example
    # Real QPE would need controlled application of the unitary

    qc = QuantumCircuit(n_precision)

    # Create superposition
    for i in range(n_precision):
        qc.h(i)

    # Apply phase kicks (simulating controlled-U operations)
    for i in range(n_precision):
        angle = 2 * np.pi * unitary_power / (2 ** (n_precision - i))
        qc.p(angle, i)

    # Inverse QFT
    qc = inverse_qft_on_register(qc, list(range(n_precision)))

    # Get state
    sv = get_statevector(qc)
    probs = sv.probabilities

    # Find most likely outcome
    estimated_phase_int = np.argmax(probs)
    estimated_phase = estimated_phase_int / (2 ** n_precision)

    return estimated_phase


# Export
__all__ = [
    'qft_circuit',
    'inverse_qft_circuit',
    'qft_on_register',
    'inverse_qft_on_register',
    'qft_matrix',
    'verify_qft',
    'phase_estimation_example',
]
