"""
Entanglement analysis: Schmidt decomposition, entropy measures, concurrence,
negativity, and related quantities.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from ..core.state_vector import StateVector
from ..core.density_matrix import DensityMatrix
from ..core.utils import partial_trace_simple


@dataclass
class SchmidtDecomposition:
    """Schmidt decomposition of a bipartite pure state."""
    coefficients: np.ndarray
    basis_a: np.ndarray
    basis_b: np.ndarray
    partition: Tuple[List[int], List[int]]

    @property
    def schmidt_rank(self) -> int:
        """Number of non-zero Schmidt coefficients."""
        return int(np.sum(self.coefficients > 1e-10))

    @property
    def is_entangled(self) -> bool:
        """True if Schmidt rank > 1."""
        return self.schmidt_rank > 1

    @property
    def entanglement_entropy(self) -> float:
        """S = -Sum lambda_i^2 log(lambda_i^2)."""
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
    """Compute the Schmidt decomposition via SVD of the reshaped state vector."""
    n = state.n_qubits
    if partition_b is None:
        partition_b = [q for q in range(n) if q not in partition_a]

    dim_a = 2 ** len(partition_a)
    dim_b = 2 ** len(partition_b)

    psi = state.amplitudes.copy()

    matrix = np.zeros((dim_a, dim_b), dtype=complex)

    for idx in range(2 ** n):
        bits_a = 0
        bits_b = 0
        for i, q in enumerate(partition_a):
            bits_a |= ((idx >> q) & 1) << i
        for i, q in enumerate(partition_b):
            bits_b |= ((idx >> q) & 1) << i
        matrix[bits_a, bits_b] = psi[idx]

    U, S, Vh = np.linalg.svd(matrix, full_matrices=False)

    return SchmidtDecomposition(
        coefficients=S,
        basis_a=U,
        basis_b=Vh.conj().T,
        partition=(partition_a, partition_b)
    )


def von_neumann_entropy(rho: np.ndarray) -> float:
    """S(rho) = -Tr(rho log2 rho)."""
    eigenvalues = np.linalg.eigvalsh(rho)
    eigenvalues = eigenvalues[eigenvalues > 1e-15]
    return float(-np.sum(eigenvalues * np.log2(eigenvalues)))


def entanglement_entropy(
    state: StateVector,
    partition_a: List[int]
) -> float:
    """Entanglement entropy S(rho_A) for a bipartition of a pure state."""
    sd = schmidt_decomposition(state, partition_a)
    return sd.entanglement_entropy


def concurrence(state: StateVector) -> float:
    """Concurrence of a 2-qubit pure state: C = 2|ad - bc|."""
    if state.n_qubits != 2:
        raise ValueError(f"Concurrence is defined for 2 qubits, got {state.n_qubits}")

    psi = state.amplitudes
    a, b, c, d = psi[0], psi[1], psi[2], psi[3]

    return float(2 * abs(a * d - b * c))


def concurrence_mixed(rho: np.ndarray) -> float:
    """Concurrence for a 2-qubit mixed state (Wootters' formula)."""
    if rho.shape != (4, 4):
        raise ValueError("Concurrence requires a 4x4 density matrix (2 qubits)")

    sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    yy = np.kron(sigma_y, sigma_y)

    R = rho @ yy @ rho.conj() @ yy
    eigenvalues = np.sort(np.real(np.linalg.eigvals(R)))[::-1]
    eigenvalues = np.maximum(eigenvalues, 0)
    sqrt_eigenvalues = np.sqrt(eigenvalues)

    return float(max(0, sqrt_eigenvalues[0] - sqrt_eigenvalues[1] - sqrt_eigenvalues[2] - sqrt_eigenvalues[3]))


def negativity(rho: np.ndarray, n_a: int, n_b: int) -> float:
    """Negativity N(rho) = (||rho^{T_B}||_1 - 1) / 2."""
    rho_pt = _partial_transpose(rho, n_a, n_b)

    eigenvalues = np.linalg.eigvalsh(rho_pt)
    trace_norm = np.sum(np.abs(eigenvalues))

    return float((trace_norm - 1) / 2)


def _partial_transpose(rho: np.ndarray, dim_a: int, dim_b: int) -> np.ndarray:
    """Partial transpose with respect to subsystem B."""
    rho_reshaped = rho.reshape(dim_a, dim_b, dim_a, dim_b)
    rho_pt = rho_reshaped.transpose(0, 3, 2, 1)
    return rho_pt.reshape(dim_a * dim_b, dim_a * dim_b)


def mutual_information(
    state: StateVector,
    partition_a: List[int],
    partition_b: Optional[List[int]] = None
) -> float:
    """Quantum mutual information I(A:B) = S(A) + S(B) - S(AB). For pure states, 2*S(A)."""
    n = state.n_qubits
    if partition_b is None:
        partition_b = [q for q in range(n) if q not in partition_a]

    s_a = entanglement_entropy(state, partition_a)
    return 2 * s_a


def entanglement_spectrum(
    state: StateVector,
    partition_a: List[int]
) -> np.ndarray:
    """Entanglement spectrum: -log(lambda_i^2) for Schmidt coefficients lambda_i."""
    sd = schmidt_decomposition(state, partition_a)
    probs = sd.coefficients ** 2
    probs = probs[probs > 1e-15]
    spectrum = -np.log(probs)
    return np.sort(spectrum)


def pairwise_entanglement(state: StateVector) -> np.ndarray:
    """Pairwise concurrence between all qubit pairs.

    Each entry (i, j) is the Wootters concurrence of the two-qubit reduced
    density matrix of qubits i and j: 1 for a Bell pair, 0 for a product state.
    """
    n = state.n_qubits
    ent_map = np.zeros((n, n))

    for i in range(n):
        for j in range(i + 1, n):
            rho_ij = state.reduced_density_matrix([i, j])
            ent = concurrence_mixed(rho_ij)
            ent_map[i, j] = ent
            ent_map[j, i] = ent

    return ent_map


def analyze_entanglement(state: StateVector) -> Dict[str, Any]:
    """Run all entanglement measures on a state."""
    n = state.n_qubits
    result = {
        'n_qubits': n,
        'is_pure': True,
    }

    single_qubit_entropies = []
    for q in range(n):
        s = entanglement_entropy(state, [q])
        single_qubit_entropies.append(float(s))
    result['single_qubit_entropies'] = single_qubit_entropies
    result['total_entanglement'] = float(sum(single_qubit_entropies))

    half = n // 2
    if half > 0:
        result['half_chain_entropy'] = float(entanglement_entropy(state, list(range(half))))

    result['pairwise_map'] = pairwise_entanglement(state).tolist()

    if half > 0:
        sd = schmidt_decomposition(state, list(range(half)))
        result['schmidt_rank'] = sd.schmidt_rank
        result['schmidt_coefficients'] = sd.coefficients.tolist()
        result['is_entangled'] = sd.is_entangled
        result['entanglement_fraction'] = sd.entanglement_fraction

    if n == 2:
        result['concurrence'] = concurrence(state)

    spectrum = entanglement_spectrum(state, [0])
    result['entanglement_spectrum'] = spectrum.tolist()

    return result


# Keep old name as alias for backwards compatibility
full_entanglement_analysis = analyze_entanglement
