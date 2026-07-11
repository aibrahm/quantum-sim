"""
Quantum Measurement Operations.
Includes projective measurements, POVM, and sampling utilities.
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class MeasurementOutcome:
    """Represents a single measurement outcome."""
    value: int  # Integer representation of outcome
    bits: str  # Binary string representation
    probability: float  # Probability of this outcome


def projective_measure(
    amplitudes: np.ndarray,
    qubits: List[int],
    n_qubits: int
) -> Tuple[int, np.ndarray]:
    """
    Perform projective measurement on specified qubits.

    Args:
        amplitudes: State vector amplitudes
        qubits: Qubit indices to measure
        n_qubits: Total number of qubits

    Returns:
        Tuple of (outcome, collapsed_state)
    """
    dim = 2 ** n_qubits
    n_measured = len(qubits)

    # Calculate probabilities for each outcome
    outcome_probs = np.zeros(2 ** n_measured)

    for i in range(dim):
        # Extract measured qubit bits
        outcome_idx = 0
        for k, q in enumerate(qubits):
            bit = (i >> q) & 1
            outcome_idx |= bit << k
        outcome_probs[outcome_idx] += np.abs(amplitudes[i]) ** 2

    # Sample outcome based on probabilities
    outcome = np.random.choice(2 ** n_measured, p=outcome_probs)

    # Collapse state
    collapsed = np.zeros(dim, dtype=complex)

    for i in range(dim):
        # Check if basis state matches outcome
        match = True
        for k, q in enumerate(qubits):
            bit = (i >> q) & 1
            expected = (outcome >> k) & 1
            if bit != expected:
                match = False
                break

        if match:
            collapsed[i] = amplitudes[i]

    # Normalize
    norm = np.linalg.norm(collapsed)
    if norm > 1e-15:
        collapsed /= norm

    return outcome, collapsed


def measure_all(amplitudes: np.ndarray, n_qubits: int) -> Tuple[int, np.ndarray]:
    """
    Measure all qubits in the computational basis.

    Args:
        amplitudes: State vector amplitudes
        n_qubits: Number of qubits

    Returns:
        Tuple of (outcome, collapsed_state)
    """
    probabilities = np.abs(amplitudes) ** 2
    outcome = np.random.choice(len(amplitudes), p=probabilities)

    # Collapsed state is the computational basis state
    collapsed = np.zeros_like(amplitudes)
    collapsed[outcome] = 1.0

    return outcome, collapsed


def sample(
    amplitudes: np.ndarray,
    n_qubits: int,
    shots: int = 1024,
    qubits: Optional[List[int]] = None
) -> Dict[str, int]:
    """
    Sample measurement outcomes without collapsing state.

    Args:
        amplitudes: State vector amplitudes
        n_qubits: Total number of qubits
        shots: Number of measurements to simulate
        qubits: Specific qubits to measure (None = all)

    Returns:
        Dictionary mapping outcome strings to counts
    """
    if qubits is None:
        qubits = list(range(n_qubits))

    n_measured = len(qubits)
    dim = len(amplitudes)

    # Calculate marginal probabilities
    outcome_probs = np.zeros(2 ** n_measured)

    for i in range(dim):
        outcome_idx = 0
        for k, q in enumerate(qubits):
            bit = (i >> q) & 1
            outcome_idx |= bit << k
        outcome_probs[outcome_idx] += np.abs(amplitudes[i]) ** 2

    # Sample outcomes
    outcomes = np.random.choice(2 ** n_measured, size=shots, p=outcome_probs)

    # Count occurrences
    counts: Dict[str, int] = {}
    for outcome in outcomes:
        key = format(outcome, f'0{n_measured}b')
        counts[key] = counts.get(key, 0) + 1

    return counts


def sample_counts_to_probabilities(counts: Dict[str, int]) -> Dict[str, float]:
    """
    Convert measurement counts to empirical probabilities.

    Args:
        counts: Dictionary of outcome counts

    Returns:
        Dictionary of probabilities
    """
    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}


def get_probabilities(
    amplitudes: np.ndarray,
    qubits: Optional[List[int]] = None,
    n_qubits: Optional[int] = None
) -> Dict[str, float]:
    """
    Get exact measurement probabilities (not sampled).

    Args:
        amplitudes: State vector
        qubits: Qubits to measure (None = all)
        n_qubits: Total number of qubits

    Returns:
        Dictionary mapping outcome strings to probabilities
    """
    dim = len(amplitudes)
    if n_qubits is None:
        n_qubits = int(np.log2(dim))

    if qubits is None:
        qubits = list(range(n_qubits))

    n_measured = len(qubits)
    probs = np.zeros(2 ** n_measured)

    for i in range(dim):
        outcome_idx = 0
        for k, q in enumerate(qubits):
            bit = (i >> q) & 1
            outcome_idx |= bit << k
        probs[outcome_idx] += np.abs(amplitudes[i]) ** 2

    return {
        format(i, f'0{n_measured}b'): float(probs[i])
        for i in range(2 ** n_measured)
        if probs[i] > 1e-15
    }


def povm_measure(
    amplitudes: np.ndarray,
    operators: List[np.ndarray],
    n_qubits: int
) -> int:
    """
    Perform POVM measurement.

    Args:
        amplitudes: State vector
        operators: List of POVM operators (positive, sum to identity)
        n_qubits: Number of qubits

    Returns:
        Index of the measurement outcome
    """
    # Calculate probabilities: p_i = ⟨ψ|E_i|ψ⟩
    probs = []
    for E in operators:
        prob = np.real(np.vdot(amplitudes, E @ amplitudes))
        probs.append(max(0, prob))  # Ensure non-negative

    # Normalize probabilities
    total = sum(probs)
    if total > 1e-15:
        probs = [p / total for p in probs]
    else:
        probs = [1.0 / len(operators)] * len(operators)

    # Sample outcome
    return int(np.random.choice(len(operators), p=probs))


def weak_measurement(
    amplitudes: np.ndarray,
    observable: np.ndarray,
    strength: float,
    n_qubits: int
) -> Tuple[float, np.ndarray]:
    """
    Perform weak measurement of an observable.

    Args:
        amplitudes: State vector
        observable: Hermitian observable to measure
        strength: Measurement strength (0 = no measurement, 1 = strong)
        n_qubits: Number of qubits

    Returns:
        Tuple of (weak_value, post_measurement_state)
    """
    # Weak value: ⟨ψ|A|ψ⟩ with perturbation
    expectation = np.real(np.vdot(amplitudes, observable @ amplitudes))

    # Add Gaussian noise inversely proportional to strength
    if strength < 1:
        noise_std = np.sqrt((1 - strength) / max(strength, 0.01))
        weak_value = expectation + np.random.normal(0, noise_std)
    else:
        weak_value = expectation

    # Partial collapse (interpolate between no collapse and full collapse)
    # This is a simplified model of weak measurement back-action
    eigenvalues, eigenvectors = np.linalg.eigh(observable)

    # Project onto eigenspaces with weights based on strength
    collapsed = np.zeros_like(amplitudes)
    for i, (val, vec) in enumerate(zip(eigenvalues, eigenvectors.T)):
        proj = np.outer(vec, np.conj(vec))
        component = proj @ amplitudes

        # Weight by proximity to measured value
        weight = np.exp(-strength * (val - weak_value) ** 2)
        collapsed += weight * component

    # Normalize
    norm = np.linalg.norm(collapsed)
    if norm > 1e-15:
        collapsed /= norm

    return weak_value, collapsed


def mid_circuit_reset(
    amplitudes: np.ndarray,
    qubit: int,
    n_qubits: int
) -> np.ndarray:
    """
    Reset a qubit to |0⟩ mid-circuit (measure and conditionally flip).

    Args:
        amplitudes: Current state vector
        qubit: Qubit to reset
        n_qubits: Total number of qubits

    Returns:
        State with qubit reset to |0⟩
    """
    # Measure the qubit
    outcome, collapsed = projective_measure(amplitudes, [qubit], n_qubits)

    # If outcome is 1, apply X gate to flip to 0
    if outcome == 1:
        dim = 2 ** n_qubits
        new_state = np.zeros(dim, dtype=complex)
        for i in range(dim):
            if (i >> qubit) & 1:  # bit is 1
                j = i ^ (1 << qubit)  # flip to 0
                new_state[j] = collapsed[i]
            else:
                new_state[i] = collapsed[i]
        return new_state

    return collapsed


def measure_in_basis(
    amplitudes: np.ndarray,
    basis: str,
    qubit: int,
    n_qubits: int
) -> Tuple[int, np.ndarray]:
    """
    Measure a qubit in a specified basis.

    Args:
        amplitudes: State vector
        basis: 'X', 'Y', or 'Z' (computational)
        qubit: Qubit to measure
        n_qubits: Total number of qubits

    Returns:
        Tuple of (outcome, collapsed_state)
    """
    from .gates import H, Sdg, tensor_gate

    # Transform to computational basis
    if basis.upper() == 'Z':
        # Already in Z basis
        pass
    elif basis.upper() == 'X':
        # Apply H to transform X basis to Z basis
        h_full = tensor_gate(H, qubit, n_qubits)
        amplitudes = h_full @ amplitudes
    elif basis.upper() == 'Y':
        # Apply Sdg then H to transform Y basis to Z basis
        sdg_full = tensor_gate(Sdg, qubit, n_qubits)
        h_full = tensor_gate(H, qubit, n_qubits)
        amplitudes = h_full @ (sdg_full @ amplitudes)
    else:
        raise ValueError(f"Unknown basis: {basis}")

    # Measure in Z basis
    outcome, collapsed = projective_measure(amplitudes, [qubit], n_qubits)

    # Transform back
    if basis.upper() == 'X':
        h_full = tensor_gate(H, qubit, n_qubits)
        collapsed = h_full @ collapsed
    elif basis.upper() == 'Y':
        from .gates import S
        h_full = tensor_gate(H, qubit, n_qubits)
        s_full = tensor_gate(S, qubit, n_qubits)
        collapsed = s_full @ (h_full @ collapsed)

    return outcome, collapsed


def expectation_value(
    amplitudes: np.ndarray,
    observable: np.ndarray,
    qubits: Optional[List[int]] = None,
    n_qubits: Optional[int] = None
) -> float:
    """
    Calculate expectation value ⟨ψ|O|ψ⟩.

    Args:
        amplitudes: State vector
        observable: Hermitian operator
        qubits: Qubits observable acts on (None = full system)
        n_qubits: Total qubits (inferred if None)

    Returns:
        Real expectation value
    """
    dim = len(amplitudes)
    if n_qubits is None:
        n_qubits = int(np.log2(dim))

    if qubits is not None:
        from .gates import multi_qubit_gate
        observable = multi_qubit_gate(observable, qubits, n_qubits)

    result = np.vdot(amplitudes, observable @ amplitudes)
    return float(np.real(result))


def estimate_expectation(
    amplitudes: np.ndarray,
    observable: np.ndarray,
    shots: int = 1000,
    n_qubits: Optional[int] = None
) -> Tuple[float, float]:
    """
    Estimate expectation value through sampling.

    Args:
        amplitudes: State vector
        observable: Hermitian observable
        shots: Number of measurement shots
        n_qubits: Total qubits

    Returns:
        Tuple of (estimated_value, standard_error)
    """
    dim = len(amplitudes)
    if n_qubits is None:
        n_qubits = int(np.log2(dim))

    # Diagonalize observable
    eigenvalues, eigenvectors = np.linalg.eigh(observable)

    # Calculate probabilities in eigenbasis
    probs = []
    for vec in eigenvectors.T:
        prob = np.abs(np.vdot(vec, amplitudes)) ** 2
        probs.append(prob)

    # Sample eigenvalues
    samples = np.random.choice(eigenvalues, size=shots, p=probs)

    mean = np.mean(samples)
    stderr = np.std(samples) / np.sqrt(shots)

    return float(mean), float(stderr)


# Export all
__all__ = [
    'MeasurementOutcome',
    'projective_measure',
    'measure_all',
    'sample',
    'sample_counts_to_probabilities',
    'get_probabilities',
    'povm_measure',
    'weak_measurement',
    'mid_circuit_reset',
    'measure_in_basis',
    'expectation_value',
    'estimate_expectation',
]
