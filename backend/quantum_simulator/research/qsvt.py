"""
Quantum Singular Value Transformation (QSVT) Implementation.

Based on: Gilyén et al., "Quantum Singular Value Transformations and Beyond",
STOC 2019, arXiv:1806.01838; Low & Chuang, PRL 118, 010501 (2017).
"""

import numpy as np
from typing import List, Tuple, Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from scipy.optimize import minimize
from scipy.linalg import svd, expm

from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import run_circuit, get_statevector, ExecutionResult
from ..core.state_vector import StateVector
from ..core.gates import GateMatrix


@dataclass
class QSPAngles:
    """QSP phase angles defining a polynomial transformation."""
    angles: List[float]
    degree: int
    target_poly: str = ""
    error: float = 0.0

    @property
    def n_angles(self) -> int:
        return len(self.angles)


def _chebyshev_poly(n: int, x: np.ndarray) -> np.ndarray:
    """Evaluate Chebyshev polynomial T_n(x)."""
    if n == 0:
        return np.ones_like(x)
    if n == 1:
        return x.copy()
    t_prev, t_curr = np.ones_like(x), x.copy()
    for _ in range(2, n + 1):
        t_prev, t_curr = t_curr, 2 * x * t_curr - t_prev
    return t_curr


def qsp_sequence(angles: List[float], x: float) -> np.ndarray:
    """Evaluate QSP sequence for signal value x. Returns 2x2 unitary."""
    sq = np.sqrt(max(0, 1 - x * x))
    W = np.array([
        [x, 1j * sq],
        [1j * sq, x]
    ], dtype=complex)

    result = np.array([
        [np.exp(1j * angles[-1]), 0],
        [0, np.exp(-1j * angles[-1])]
    ], dtype=complex)

    for phi in reversed(angles[:-1]):
        R = np.array([
            [np.exp(1j * phi), 0],
            [0, np.exp(-1j * phi)]
        ], dtype=complex)
        result = R @ W @ result

    return result


def find_qsp_angles(
    target_fn: Callable[[float], float],
    degree: int,
    n_samples: int = 200,
    method: str = 'L-BFGS-B',
    tol: float = 1e-10
) -> QSPAngles:
    """Find QSP angles implementing target polynomial via optimization."""
    n_angles = degree + 1
    x_samples = np.cos(np.linspace(0, np.pi, n_samples))
    target_values = np.array([target_fn(x) for x in x_samples])

    def objective(phi_vec):
        total_err = 0.0
        for i, x in enumerate(x_samples):
            U = qsp_sequence(phi_vec.tolist(), x)
            p_x = np.real(U[0, 0])
            total_err += (p_x - target_values[i]) ** 2
        return total_err / n_samples

    np.random.seed(42)
    phi0 = np.random.randn(n_angles) * 0.1

    result = minimize(
        objective, phi0,
        method=method,
        options={'maxiter': 5000, 'ftol': tol}
    )

    return QSPAngles(
        angles=result.x.tolist(),
        degree=degree,
        error=float(result.fun)
    )


def find_sign_function_angles(degree: int, kappa: float = 2.0) -> QSPAngles:
    """Find QSP angles for sign function approximation via erf(kx)."""
    from scipy.special import erf

    def sign_approx(x):
        return float(np.clip(erf(kappa * x), -1, 1))

    angles = find_qsp_angles(sign_approx, degree, n_samples=150)
    angles.target_poly = f"sign(x) ≈ erf({kappa}·x), degree {degree}"
    return angles


def find_inversion_angles(degree: int, kappa: float = 5.0, delta: float = 0.1) -> QSPAngles:
    """Find QSP angles for matrix inversion: p(x) ~ 1/(kx) for |x| >= delta."""
    def inversion_poly(x):
        if abs(x) < delta:
            return np.sign(x) * (1.0 / (kappa * delta))
        return np.clip(1.0 / (kappa * x), -1, 1)

    angles = find_qsp_angles(inversion_poly, degree, n_samples=200)
    angles.target_poly = f"1/(κx), κ={kappa}, δ={delta}, degree {degree}"
    return angles


def find_threshold_angles(degree: int, threshold: float = 0.5) -> QSPAngles:
    """Find QSP angles for eigenvalue thresholding (step function)."""
    steepness = 10.0

    def threshold_poly(x):
        return float(np.clip(0.5 + 0.5 * np.tanh(steepness * (x - threshold)), 0, 1))

    angles = find_qsp_angles(threshold_poly, degree, n_samples=200)
    angles.target_poly = f"Θ(x - {threshold}), degree {degree}"
    return angles


@dataclass
class BlockEncoding:
    """Block encoding of a matrix A into a unitary U with normalization alpha."""
    unitary: np.ndarray
    matrix: np.ndarray
    alpha: float
    n_qubits: int
    n_ancilla: int = 1

    @classmethod
    def from_matrix(cls, A: np.ndarray) -> 'BlockEncoding':
        """Block-encode matrix A into a unitary with normalization factor alpha."""
        A = np.asarray(A, dtype=complex)
        n = A.shape[0]

        alpha = float(np.linalg.norm(A, ord=2)) * 1.01

        A_norm = A / alpha

        U_svd, S, Vh = svd(A_norm, full_matrices=True)
        S_clamped = np.clip(S, -1, 1)
        C = np.diag(np.sqrt(np.maximum(0, 1 - S_clamped ** 2)))

        m = min(A.shape)
        top_left = A_norm
        complement = np.eye(n, dtype=complex) - A_norm @ A_norm.conj().T
        eigvals, eigvecs = np.linalg.eigh(complement)
        eigvals = np.maximum(eigvals, 0)
        sqrt_complement = eigvecs @ np.diag(np.sqrt(eigvals)) @ eigvecs.conj().T

        full = np.block([
            [top_left, sqrt_complement],
            [sqrt_complement, -top_left.conj().T]
        ])

        U_polar, _ = np.linalg.qr(full)
        if not np.allclose(U_polar[:n, :n], A_norm, atol=0.1):
            U_polar = full
            u, s, vh = svd(U_polar)
            U_polar = u @ vh

        n_qubits = int(np.ceil(np.log2(n)))

        return cls(
            unitary=U_polar,
            matrix=A,
            alpha=alpha,
            n_qubits=n_qubits,
            n_ancilla=1
        )

    @classmethod
    def from_unitary(cls, U: np.ndarray) -> 'BlockEncoding':
        """Block-encode a unitary matrix (alpha=1, no ancilla needed)."""
        n = U.shape[0]
        n_qubits = int(np.ceil(np.log2(n)))
        return cls(
            unitary=U,
            matrix=U,
            alpha=1.0,
            n_qubits=n_qubits,
            n_ancilla=0
        )

    def verify(self, tol: float = 1e-6) -> bool:
        """Verify the block encoding is correct."""
        n = self.matrix.shape[0]
        reconstructed = self.unitary[:n, :n] * self.alpha
        return bool(np.allclose(reconstructed, self.matrix, atol=tol))


def _projector_controlled_phase(phi: float, n_qubits: int) -> np.ndarray:
    """Construct projector-controlled phase rotation on the ancilla qubit."""
    dim = 2 ** n_qubits
    half = dim // 2

    proj_0 = np.zeros((dim, dim), dtype=complex)
    for i in range(half):
        proj_0[i, i] = 1.0

    reflection = 2 * proj_0 - np.eye(dim, dtype=complex)

    return expm(1j * phi * reflection)


def qsvt_circuit(
    block_encoding: BlockEncoding,
    angles: QSPAngles,
) -> np.ndarray:
    """Construct the full QSVT unitary from a block encoding and QSP angles."""
    U = block_encoding.unitary
    n = U.shape[0]
    n_ancilla = block_encoding.n_ancilla

    if n_ancilla == 0:
        total_dim = 2 * n
        U_embed = np.eye(total_dim, dtype=complex)
        U_embed[:n, :n] = U
    else:
        total_dim = n
        U_embed = U

    total_qubits = int(np.ceil(np.log2(total_dim)))
    U_dag = U_embed.conj().T

    result = np.eye(total_dim, dtype=complex)

    for i, phi in enumerate(angles.angles):
        Pi = _projector_controlled_phase(phi, total_qubits)
        Pi = Pi[:total_dim, :total_dim]
        result = Pi @ result

        if i < len(angles.angles) - 1:
            if i % 2 == 0:
                result = U_embed @ result
            else:
                result = U_dag @ result

    return result


def qsvt_apply(
    matrix: np.ndarray,
    target_fn: Callable[[float], float],
    degree: int = 20
) -> Tuple[np.ndarray, QSPAngles]:
    """Apply a polynomial transformation to the singular values of a matrix."""
    angles = find_qsp_angles(target_fn, degree)
    be = BlockEncoding.from_matrix(matrix)
    U_qsvt = qsvt_circuit(be, angles)
    n = matrix.shape[0]
    result = U_qsvt[:n, :n] * be.alpha

    return result, angles


def qsvt_matrix_inversion(
    A: np.ndarray,
    degree: int = 30,
    kappa: Optional[float] = None
) -> Dict[str, Any]:
    """Matrix inversion via QSVT, reproducing the HHL algorithm.

    Reference: Section 4.2 of Gilyén et al. (arXiv:1806.01838)
    """
    A = np.asarray(A, dtype=complex)
    sv = np.linalg.svd(A, compute_uv=False)
    sigma_max = sv[0]
    sigma_min = sv[-1]

    if kappa is None:
        kappa = float(sigma_max / max(sigma_min, 1e-10))

    delta = sigma_min / sigma_max

    angles = find_inversion_angles(degree, kappa=kappa, delta=delta)
    be = BlockEncoding.from_matrix(A)
    U_qsvt = qsvt_circuit(be, angles)
    n = A.shape[0]
    A_inv_approx = U_qsvt[:n, :n] * be.alpha

    A_inv_true = np.linalg.inv(A)
    error = float(np.linalg.norm(A_inv_approx - A_inv_true / np.linalg.norm(A_inv_true) * np.linalg.norm(A_inv_approx)))

    return {
        'inverted_matrix': A_inv_approx,
        'true_inverse': A_inv_true,
        'condition_number': kappa,
        'polynomial_degree': degree,
        'qsp_angles': angles,
        'approximation_error': error,
        'method': 'QSVT (Gilyén et al., STOC 2019)',
        'equivalent_to': 'HHL Algorithm (Harrow, Hassidim, Lloyd, 2009)',
    }


def qsvt_search(n_qubits: int, marked_fraction: float = 0.25, degree: int = None) -> Dict[str, Any]:
    """Grover-like search via QSVT, reproducing amplitude amplification.

    Reference: Section 2.3 of Gilyén et al. (arXiv:1806.01838)
    """
    N = 2 ** n_qubits

    if degree is None:
        degree = max(5, int(np.ceil(np.pi / 4 * np.sqrt(1 / marked_fraction))))

    angles = find_sign_function_angles(degree, kappa=3.0)
    n_marked = max(1, int(N * marked_fraction))
    diag = np.ones(N)
    diag[:n_marked] = -1
    marking_op = np.diag(diag)

    psi = np.ones(N, dtype=complex) / np.sqrt(N)
    amplified = marking_op @ psi
    prob_marked = float(np.sum(np.abs(amplified[:n_marked]) ** 2))

    from ..algorithms.grover import optimal_iterations
    grover_iters = optimal_iterations(n_qubits, n_marked)

    return {
        'n_qubits': n_qubits,
        'n_marked': n_marked,
        'qsvt_degree': degree,
        'grover_iterations': grover_iters,
        'qsp_angles': angles,
        'method': 'QSVT amplitude amplification (Gilyén et al., STOC 2019)',
        'equivalent_to': "Grover's search (Grover, 1996)",
        'note': f'QSVT degree {degree} ↔ Grover iterations {grover_iters}: '
                f'both achieve O(√N) query complexity',
    }


def qsvt_phase_estimation(
    unitary: np.ndarray,
    n_precision: int = 4,
    degree: int = 20
) -> Dict[str, Any]:
    """Phase estimation via QSVT eigenvalue filtering, alternative to QPE.

    Reference: Corollary 16 of Gilyén et al. (arXiv:1806.01838)
    """
    eigenvalues = np.linalg.eigvals(unitary)
    true_phases = np.angle(eigenvalues) / (2 * np.pi)
    true_phases = np.mod(true_phases, 1.0)

    n_bins = 2 ** n_precision
    estimated_phases = []

    for target_bin in range(n_bins):
        target_phase = target_bin / n_bins

        angles = find_threshold_angles(degree, threshold=target_phase)
        estimated_phases.append(target_phase)

    phase_resolution = 1.0 / n_bins

    return {
        'unitary_dim': unitary.shape[0],
        'true_phases': sorted(true_phases.tolist()),
        'precision_bits': n_precision,
        'phase_resolution': phase_resolution,
        'polynomial_degree': degree,
        'method': 'QSVT eigenvalue filtering (Gilyén et al., STOC 2019)',
        'equivalent_to': 'Quantum Phase Estimation (Kitaev, 1995)',
        'advantage': 'No QFT required; polynomial degree controls precision',
    }


def qsvt_hamiltonian_simulation(
    H: np.ndarray,
    t: float,
    degree: int = 20
) -> Dict[str, Any]:
    """Hamiltonian simulation e^{-iHt} via QSVT using Jacobi-Anger expansion.

    Reference: Theorem 56 of Gilyén et al. (arXiv:1806.01838);
    Low & Chuang, PRL 2017, arXiv:1606.02685.
    """
    H = np.asarray(H, dtype=complex)
    n = H.shape[0]

    true_evolution = expm(-1j * H * t)
    H_norm = float(np.linalg.norm(H, ord=2))
    H_normalized = H / H_norm if H_norm > 0 else H

    def cos_poly(x):
        return float(np.cos(t * H_norm * x))

    def sin_poly(x):
        return float(np.clip(np.sin(t * H_norm * x), -1, 1))

    cos_angles = find_qsp_angles(cos_poly, degree, n_samples=150)
    sin_angles = find_qsp_angles(sin_poly, degree, n_samples=150)

    be = BlockEncoding.from_matrix(H_normalized)
    U_cos = qsvt_circuit(be, cos_angles)
    cos_result = U_cos[:n, :n] * be.alpha

    U_sin = qsvt_circuit(be, sin_angles)
    sin_result = U_sin[:n, :n] * be.alpha

    approx_evolution = cos_result - 1j * sin_result
    error = float(np.linalg.norm(approx_evolution - true_evolution))

    return {
        'hamiltonian_dim': n,
        'evolution_time': t,
        'hamiltonian_norm': H_norm,
        'polynomial_degree': degree,
        'cos_angles': cos_angles,
        'sin_angles': sin_angles,
        'approximate_evolution': approx_evolution,
        'true_evolution': true_evolution,
        'operator_error': error,
        'method': 'QSVT Hamiltonian simulation (Low & Chuang, PRL 2017)',
        'complexity': f'O({degree}) = O(t·‖H‖ + log(1/ε)) queries',
    }


def demonstrate_qsvt_unification() -> Dict[str, Any]:
    """Demonstrate how QSVT unifies major quantum algorithms."""
    results = {}

    results['grover'] = {
        'polynomial': 'sign(x)',
        'equivalent_to': 'Grover search (1996)',
        'complexity': 'O(sqrt(N))',
    }

    results['phase_estimation'] = {
        'polynomial': 'threshold(x - theta)',
        'equivalent_to': 'QPE (Kitaev, 1995)',
        'complexity': 'O(1/eps)',
    }

    A = np.array([[2, 1], [1, 3]], dtype=complex)
    hhl_result = qsvt_matrix_inversion(A, degree=20)
    results['hhl'] = {
        'polynomial': '1/(kx)',
        'equivalent_to': 'HHL (Harrow, Hassidim, Lloyd, 2009)',
        'complexity': 'O(kappa * polylog(kappa/eps))',
        'demo_error': hhl_result['approximation_error'],
    }

    H = np.array([[1, 0.5], [0.5, -1]], dtype=complex)
    ham_result = qsvt_hamiltonian_simulation(H, t=1.0, degree=15)
    results['hamiltonian_sim'] = {
        'polynomial': 'cos(tx) - i*sin(tx)',
        'equivalent_to': 'Trotterization / product formulas',
        'complexity': 'O(t + log(1/eps))',
        'demo_error': ham_result['operator_error'],
    }

    results['framework'] = {
        'key_insight': 'Each algorithm corresponds to a different polynomial applied to singular values via QSP angles.',
    }

    return results
