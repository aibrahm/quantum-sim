"""
Entanglement Analysis Module.

Provides tools for quantifying and analyzing quantum entanglement:
- Schmidt decomposition
- Von Neumann entropy
- Entanglement entropy
- Concurrence (2-qubit entanglement measure)
- Negativity (general mixed-state entanglement)
- Mutual information
- Entanglement spectrum

These measures are essential for understanding quantum correlations
and verifying that quantum circuits produce genuinely entangled states.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from ..core.state_vector import StateVector
from ..core.density_matrix import DensityMatrix
from ..core.utils import partial_trace_simple


# =============================================================================
# Schmidt Decomposition
# =============================================================================

@dataclass
class SchmidtDecomposition:
    """
    Schmidt decomposition of a bipartite pure state.

    Any pure state |ψ⟩ ∈ H_A ⊗ H_B can be written as:
    |ψ⟩ = Σᵢ λᵢ |αᵢ⟩_A ⊗ |βᵢ⟩_B

    where λᵢ ≥ 0 are the Schmidt coefficients (singular values)
    and |αᵢ⟩, |βᵢ⟩ are orthonormal bases for A and B.

    The Schmidt rank (number of non-zero coefficients) determines
    whether the state is entangled (rank > 1) or separable (rank = 1).
    """
    coefficients: np.ndarray  # Schmidt coefficients λᵢ
    basis_a: np.ndarray       # Basis vectors for subsystem A
    basis_b: np.ndarray       # Basis vectors for subsystem B
    partition: Tuple[List[int], List[int]]  # (qubits_A, qubits_B)

    @property
    def schmidt_rank(self) -> int:
        """Number of non-zero Schmidt coefficients."""
        return int(np.sum(self.coefficients > 1e-10))

    @property
    def is_entangled(self) -> bool:
        """True if the state is entangled (Schmidt rank > 1)."""
        return self.schmidt_rank > 1

    @property
    def entanglement_entropy(self) -> float:
        """Von Neumann entropy of the reduced state: S = -Σ λᵢ² log(λᵢ²)."""
        probs = self.coefficients ** 2
        probs = probs[probs > 1e-15]
        return float(-np.sum(probs * np.log2(probs)))

    @property
    def max_entanglement(self) -> float:
        """Maximum possible entanglement entropy for this partition."""
        d = min(len(self.coefficients), 2 ** len(self.partition[0]), 2 ** len(self.partition[1]))
        return float(np.log2(d))

    @property
    def entanglement_fraction(self) -> float:
        """Entanglement as fraction of maximum (0 = separable, 1 = maximally entangled)."""
        max_ent = self.max_entanglement
        if max_ent < 1e-15:
            return 0.0
        return self.entanglement_entropy / max_ent


def schmidt_decomposition(
    state: StateVector,
    partition_a: List[int],
    partition_b: Optional[List[int]] = None
) -> SchmidtDecomposition:
    """
    Compute the Schmidt decomposition of a pure state.

    Reshapes the state vector into a matrix (A × B), then computes SVD.

    Args:
        state: Pure quantum state
        partition_a: Qubit indices for subsystem A
        partition_b: Qubit indices for subsystem B (complement of A if None)

    Returns:
        SchmidtDecomposition with coefficients and bases
    """
    n = state.n_qubits
    if partition_b is None:
        partition_b = [q for q in range(n) if q not in partition_a]

    dim_a = 2 ** len(partition_a)
    dim_b = 2 ** len(partition_b)

    # Reorder amplitudes to group A and B qubits
    psi = state.amplitudes.copy()

    # Build reshaped matrix by reordering qubit indices
    matrix = np.zeros((dim_a, dim_b), dtype=complex)

    for idx in range(2 ** n):
        # Extract bits for A and B
        bits_a = 0
        bits_b = 0
        for i, q in enumerate(partition_a):
            bits_a |= ((idx >> q) & 1) << i
        for i, q in enumerate(partition_b):
            bits_b |= ((idx >> q) & 1) << i
        matrix[bits_a, bits_b] = psi[idx]

    # SVD gives Schmidt decomposition
    U, S, Vh = np.linalg.svd(matrix, full_matrices=False)

    return SchmidtDecomposition(
        coefficients=S,
        basis_a=U,
        basis_b=Vh.conj().T,
        partition=(partition_a, partition_b)
    )


# =============================================================================
# Entanglement Measures
# =============================================================================

def von_neumann_entropy(rho: np.ndarray) -> float:
    """
    Compute the von Neumann entropy S(ρ) = -Tr(ρ log₂ ρ).

    For a pure state, S = 0. For a maximally mixed state of dimension d, S = log₂(d).

    Args:
        rho: Density matrix

    Returns:
        Von Neumann entropy in bits
    """
    eigenvalues = np.linalg.eigvalsh(rho)
    eigenvalues = eigenvalues[eigenvalues > 1e-15]
    return float(-np.sum(eigenvalues * np.log2(eigenvalues)))


def entanglement_entropy(
    state: StateVector,
    partition_a: List[int]
) -> float:
    """
    Compute entanglement entropy for a bipartition.

    S(A) = S(ρ_A) where ρ_A = Tr_B(|ψ⟩⟨ψ|).

    This equals the Shannon entropy of the squared Schmidt coefficients.

    Args:
        state: Pure quantum state
        partition_a: Qubit indices for subsystem A

    Returns:
        Entanglement entropy in bits
    """
    sd = schmidt_decomposition(state, partition_a)
    return sd.entanglement_entropy


def concurrence(state: StateVector) -> float:
    """
    Compute the concurrence of a 2-qubit state.

    Concurrence C ∈ [0, 1] quantifies entanglement:
    - C = 0 for separable states
    - C = 1 for maximally entangled states (Bell states)

    For a pure state |ψ⟩:
    C(ψ) = 2|ad - bc| where |ψ⟩ = a|00⟩ + b|01⟩ + c|10⟩ + d|11⟩

    Args:
        state: 2-qubit pure state

    Returns:
        Concurrence value
    """
    if state.n_qubits != 2:
        raise ValueError(f"Concurrence is defined for 2 qubits, got {state.n_qubits}")

    psi = state.amplitudes
    a, b, c, d = psi[0], psi[1], psi[2], psi[3]

    return float(2 * abs(a * d - b * c))


def concurrence_mixed(rho: np.ndarray) -> float:
    """
    Compute concurrence for a 2-qubit mixed state (Wootters' formula).

    C(ρ) = max(0, λ₁ - λ₂ - λ₃ - λ₄)

    where λᵢ are the square roots of the eigenvalues (in decreasing order)
    of ρ · (σ_y ⊗ σ_y) · ρ* · (σ_y ⊗ σ_y).

    Reference: Wootters, "Entanglement of Formation of an Arbitrary
    State of Two Qubits", Physical Review Letters 80, 2245 (1998)

    Args:
        rho: 2-qubit density matrix (4×4)

    Returns:
        Concurrence value
    """
    if rho.shape != (4, 4):
        raise ValueError("Concurrence requires a 4×4 density matrix (2 qubits)")

    sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    yy = np.kron(sigma_y, sigma_y)

    # R = ρ · (σ_y ⊗ σ_y) · ρ* · (σ_y ⊗ σ_y)
    R = rho @ yy @ rho.conj() @ yy
    eigenvalues = np.sort(np.real(np.linalg.eigvals(R)))[::-1]
    eigenvalues = np.maximum(eigenvalues, 0)
    sqrt_eigenvalues = np.sqrt(eigenvalues)

    return float(max(0, sqrt_eigenvalues[0] - sqrt_eigenvalues[1] - sqrt_eigenvalues[2] - sqrt_eigenvalues[3]))


def negativity(rho: np.ndarray, n_a: int, n_b: int) -> float:
    """
    Compute the negativity of a bipartite mixed state.

    N(ρ) = (‖ρ^{T_B}‖₁ - 1) / 2

    where ρ^{T_B} is the partial transpose with respect to subsystem B.
    Negativity > 0 implies entanglement (for 2×2 and 2×3 systems, iff).

    Args:
        rho: Density matrix of the full system
        n_a: Dimension of subsystem A
        n_b: Dimension of subsystem B

    Returns:
        Negativity value (0 for separable states)
    """
    # Partial transpose with respect to B
    rho_pt = _partial_transpose(rho, n_a, n_b)

    # Compute trace norm
    eigenvalues = np.linalg.eigvalsh(rho_pt)
    trace_norm = np.sum(np.abs(eigenvalues))

    return float((trace_norm - 1) / 2)


def _partial_transpose(rho: np.ndarray, dim_a: int, dim_b: int) -> np.ndarray:
    """Compute partial transpose with respect to subsystem B."""
    rho_reshaped = rho.reshape(dim_a, dim_b, dim_a, dim_b)
    # Transpose B indices: (a, b, a', b') -> (a, b', a', b)
    rho_pt = rho_reshaped.transpose(0, 3, 2, 1)
    return rho_pt.reshape(dim_a * dim_b, dim_a * dim_b)


def mutual_information(
    state: StateVector,
    partition_a: List[int],
    partition_b: Optional[List[int]] = None
) -> float:
    """
    Compute quantum mutual information I(A:B) = S(A) + S(B) - S(AB).

    For a pure state, S(AB) = 0, so I(A:B) = 2·S(A).
    Mutual information quantifies total correlations (classical + quantum).

    Args:
        state: Pure quantum state
        partition_a: Qubit indices for A
        partition_b: Qubit indices for B (complement of A if None)

    Returns:
        Mutual information in bits
    """
    n = state.n_qubits
    if partition_b is None:
        partition_b = [q for q in range(n) if q not in partition_a]

    # For pure states: I(A:B) = 2 * S(A)
    s_a = entanglement_entropy(state, partition_a)
    return 2 * s_a


def entanglement_spectrum(
    state: StateVector,
    partition_a: List[int]
) -> np.ndarray:
    """
    Compute the entanglement spectrum: -log(λᵢ²) for Schmidt coefficients λᵢ.

    The entanglement spectrum reveals the structure of entanglement
    and is related to the energy spectrum of the entanglement Hamiltonian.
    It has applications in topological order detection and many-body physics.

    Args:
        state: Pure quantum state
        partition_a: Qubit indices for subsystem A

    Returns:
        Entanglement spectrum (sorted in ascending order)
    """
    sd = schmidt_decomposition(state, partition_a)
    probs = sd.coefficients ** 2
    probs = probs[probs > 1e-15]
    spectrum = -np.log(probs)
    return np.sort(spectrum)


# =============================================================================
# Pairwise Entanglement Map
# =============================================================================

def pairwise_entanglement(state: StateVector) -> np.ndarray:
    """
    Compute pairwise entanglement between all qubit pairs.

    Returns an n×n matrix where entry (i,j) is the entanglement
    entropy between qubit i and the rest of the system when
    partitioning at qubit i vs qubit j.

    For 2-qubit reduced states, uses concurrence as the measure.

    Args:
        state: Multi-qubit pure state

    Returns:
        n×n entanglement matrix
    """
    n = state.n_qubits
    ent_map = np.zeros((n, n))

    for i in range(n):
        for j in range(i + 1, n):
            # Compute entanglement entropy for partition {i} vs {j}
            # by tracing out all other qubits
            ent = entanglement_entropy(state, [i])
            ent_map[i, j] = ent
            ent_map[j, i] = ent

    return ent_map


def full_entanglement_analysis(state: StateVector) -> Dict[str, Any]:
    """
    Comprehensive entanglement analysis of a quantum state.

    Args:
        state: Pure quantum state

    Returns:
        Dictionary with all entanglement measures
    """
    n = state.n_qubits
    result = {
        'n_qubits': n,
        'is_pure': True,
    }

    # Single-qubit entanglement entropies
    single_qubit_entropies = []
    for q in range(n):
        s = entanglement_entropy(state, [q])
        single_qubit_entropies.append(float(s))
    result['single_qubit_entropies'] = single_qubit_entropies
    result['total_entanglement'] = float(sum(single_qubit_entropies))

    # Half-chain entanglement entropy (standard measure for 1D systems)
    half = n // 2
    if half > 0:
        result['half_chain_entropy'] = float(entanglement_entropy(state, list(range(half))))

    # Pairwise entanglement map
    result['pairwise_map'] = pairwise_entanglement(state).tolist()

    # Schmidt decomposition for equal bipartition
    if half > 0:
        sd = schmidt_decomposition(state, list(range(half)))
        result['schmidt_rank'] = sd.schmidt_rank
        result['schmidt_coefficients'] = sd.coefficients.tolist()
        result['is_entangled'] = sd.is_entangled
        result['entanglement_fraction'] = sd.entanglement_fraction

    # Concurrence for 2-qubit states
    if n == 2:
        result['concurrence'] = concurrence(state)

    # Entanglement spectrum for first qubit
    spectrum = entanglement_spectrum(state, [0])
    result['entanglement_spectrum'] = spectrum.tolist()

    return result


# Export
__all__ = [
    'SchmidtDecomposition',
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
