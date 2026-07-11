"""Utility functions for quantum simulation."""

import numpy as np
from typing import List, Tuple, Optional
from functools import reduce


def tensor_product(*matrices: np.ndarray) -> np.ndarray:
    """Kronecker product of multiple matrices."""
    if len(matrices) == 0:
        return np.array([[1]], dtype=complex)
    if len(matrices) == 1:
        return matrices[0].astype(complex)

    return reduce(np.kron, matrices).astype(complex)


def partial_trace(rho: np.ndarray, keep_qubits: List[int], n_qubits: int) -> np.ndarray:
    """Partial trace of a density matrix, keeping specified qubits."""
    if len(keep_qubits) == n_qubits:
        return rho.copy()

    if len(keep_qubits) == 0:
        return np.array([[np.trace(rho)]], dtype=complex)

    # Reshape density matrix to tensor with 2n indices
    # rho[i1,i2,...,in, j1,j2,...,jn] where each index is 0 or 1
    shape = [2] * (2 * n_qubits)
    rho_tensor = rho.reshape(shape)

    # Determine which qubits to trace out
    trace_qubits = sorted([q for q in range(n_qubits) if q not in keep_qubits], reverse=True)

    # Trace out qubits one by one from highest to lowest index
    result = rho_tensor
    for q in trace_qubits:
        # Qubit q corresponds to axes q (bra) and q + n_remaining (ket) in current tensor
        n_remaining = result.ndim // 2
        bra_axis = n_remaining - 1 - q  # Reversed indexing
        ket_axis = 2 * n_remaining - 1 - q

        # Adjust for already removed axes
        for traced_q in trace_qubits:
            if traced_q > q:
                if bra_axis > n_remaining - 1 - traced_q:
                    bra_axis -= 1
                if ket_axis > 2 * n_remaining - 1 - traced_q:
                    ket_axis -= 1

        result = np.trace(result, axis1=bra_axis, axis2=ket_axis)

    # Reshape back to matrix form
    n_keep = len(keep_qubits)
    dim = 2 ** n_keep
    return result.reshape(dim, dim)


def partial_trace_simple(rho: np.ndarray, trace_out: List[int], n_qubits: int) -> np.ndarray:
    """Partial trace via explicit summation over traced-out qubits."""
    keep_qubits = [q for q in range(n_qubits) if q not in trace_out]
    n_keep = len(keep_qubits)
    n_trace = len(trace_out)

    if n_trace == 0:
        return rho.copy()

    dim_keep = 2 ** n_keep
    dim_trace = 2 ** n_trace

    result = np.zeros((dim_keep, dim_keep), dtype=complex)

    for i in range(dim_keep):
        for j in range(dim_keep):
            # Build bit patterns for kept qubits
            i_bits = [(i >> k) & 1 for k in range(n_keep)]
            j_bits = [(j >> k) & 1 for k in range(n_keep)]

            # Sum over traced qubits
            for t in range(dim_trace):
                t_bits = [(t >> k) & 1 for k in range(n_trace)]

                # Construct full indices
                i_full = 0
                j_full = 0
                keep_idx = 0
                trace_idx = 0

                for q in range(n_qubits):
                    if q in keep_qubits:
                        i_full |= i_bits[keep_idx] << q
                        j_full |= j_bits[keep_idx] << q
                        keep_idx += 1
                    else:
                        i_full |= t_bits[trace_idx] << q
                        j_full |= t_bits[trace_idx] << q
                        trace_idx += 1

                result[i, j] += rho[i_full, j_full]

    return result


def state_to_bloch(state: np.ndarray) -> Tuple[float, float, float]:
    """Convert a single-qubit state (vector or 2x2 density matrix) to Bloch (x,y,z)."""
    state = np.asarray(state)

    # Check if it's a density matrix
    if state.shape == (2, 2):
        # For density matrix: r = (⟨X⟩, ⟨Y⟩, ⟨Z⟩)
        from .gates import X, Y, Z
        x = np.real(np.trace(state @ X))
        y = np.real(np.trace(state @ Y))
        z = np.real(np.trace(state @ Z))
        return (float(x), float(y), float(z))

    # For state vector
    if state.shape != (2,) and state.shape != (2, 1):
        raise ValueError(f"Expected 2D state vector or 2x2 density matrix, got shape {state.shape}")

    state = state.flatten()

    # Normalize
    state = state / np.linalg.norm(state)

    alpha = state[0]
    beta = state[1]

    # Handle global phase: make alpha real and positive
    if np.abs(alpha) > 1e-10:
        phase = np.exp(-1j * np.angle(alpha))
        alpha = np.abs(alpha)
        beta = beta * phase

    # Calculate Bloch coordinates
    # |ψ⟩ = cos(θ/2)|0⟩ + e^(iφ)sin(θ/2)|1⟩
    # cos(θ/2) = |α|, sin(θ/2) = |β|
    # φ = arg(β)

    cos_theta_half = np.abs(alpha)
    sin_theta_half = np.abs(beta)

    # Clamp for numerical stability
    cos_theta_half = np.clip(cos_theta_half, 0, 1)
    sin_theta_half = np.clip(sin_theta_half, 0, 1)

    theta = 2 * np.arccos(cos_theta_half)
    phi = np.angle(beta) if np.abs(beta) > 1e-10 else 0

    x = np.sin(theta) * np.cos(phi)
    y = np.sin(theta) * np.sin(phi)
    z = np.cos(theta)

    return (float(x), float(y), float(z))


def bloch_to_state(x: float, y: float, z: float) -> np.ndarray:
    """Convert Bloch sphere coordinates to a state vector."""
    r = np.sqrt(x**2 + y**2 + z**2)

    if r > 1 + 1e-10:
        raise ValueError(f"Invalid Bloch coordinates: r = {r} > 1")

    if r < 1e-10:
        # Maximally mixed state - return |0⟩ by convention
        return np.array([1, 0], dtype=complex)

    # Normalize to unit sphere for pure state
    x, y, z = x/r, y/r, z/r

    # θ = arccos(z), φ = atan2(y, x)
    theta = np.arccos(np.clip(z, -1, 1))
    phi = np.arctan2(y, x)

    # |ψ⟩ = cos(θ/2)|0⟩ + e^(iφ)sin(θ/2)|1⟩
    alpha = np.cos(theta / 2)
    beta = np.exp(1j * phi) * np.sin(theta / 2)

    return np.array([alpha, beta], dtype=complex)


def computational_basis(n_qubits: int) -> List[str]:
    """Generate computational basis state labels."""
    return [format(i, f'0{n_qubits}b') for i in range(2**n_qubits)]


def state_label(index: int, n_qubits: int) -> str:
    """Ket label for a basis state index, e.g. '|010>'."""
    return f"|{format(index, f'0{n_qubits}b')}⟩"


def embed_operator(op: np.ndarray, qubits: List[int], n_qubits: int) -> np.ndarray:
    """Embed an operator into the full Hilbert space."""
    from .gates import multi_qubit_gate
    return multi_qubit_gate(op, qubits, n_qubits)


def swap_qubits(state: np.ndarray, qubit1: int, qubit2: int, n_qubits: int) -> np.ndarray:
    """Swap two qubits in a state vector."""
    dim = 2 ** n_qubits
    result = np.zeros(dim, dtype=complex)

    for i in range(dim):
        # Get bits at qubit1 and qubit2
        bit1 = (i >> qubit1) & 1
        bit2 = (i >> qubit2) & 1

        # Swap the bits
        j = i
        if bit1 != bit2:
            j ^= (1 << qubit1)  # Flip bit at qubit1
            j ^= (1 << qubit2)  # Flip bit at qubit2

        result[j] = state[i]

    return result


def reorder_qubits(state: np.ndarray, new_order: List[int], n_qubits: int) -> np.ndarray:
    """Reorder qubits in a state vector by permutation."""
    dim = 2 ** n_qubits
    result = np.zeros(dim, dtype=complex)

    for i in range(dim):
        # Map old index to new index
        new_i = 0
        for new_pos, old_pos in enumerate(new_order):
            bit = (i >> old_pos) & 1
            new_i |= bit << new_pos
        result[new_i] = state[i]

    return result


def fidelity_pure_states(state1: np.ndarray, state2: np.ndarray) -> float:
    """Fidelity |<psi1|psi2>|^2 between two pure states."""
    overlap = np.vdot(state1, state2)
    return float(np.abs(overlap) ** 2)


def inner_product(state1: np.ndarray, state2: np.ndarray) -> complex:
    """
    Calculate inner product ⟨state1|state2⟩.
    """
    return complex(np.vdot(state1, state2))


def outer_product(state1: np.ndarray, state2: np.ndarray) -> np.ndarray:
    """
    Calculate outer product |state1⟩⟨state2|.
    """
    return np.outer(state1, np.conj(state2))


def projector(state: np.ndarray) -> np.ndarray:
    """
    Create projection operator |ψ⟩⟨ψ|.
    """
    return outer_product(state, state)


def commutator(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Calculate commutator [A, B] = AB - BA.
    """
    return A @ B - B @ A


def anticommutator(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Calculate anticommutator {A, B} = AB + BA.
    """
    return A @ B + B @ A


def is_hermitian(matrix: np.ndarray, tol: float = 1e-10) -> bool:
    """
    Check if a matrix is Hermitian.
    """
    return np.allclose(matrix, matrix.conj().T, atol=tol)


def is_positive_semidefinite(matrix: np.ndarray, tol: float = 1e-10) -> bool:
    """
    Check if a matrix is positive semidefinite.
    """
    eigenvalues = np.linalg.eigvalsh(matrix)
    return np.all(eigenvalues >= -tol)


def normalize_state(state: np.ndarray) -> np.ndarray:
    """
    Normalize a state vector.
    """
    norm = np.linalg.norm(state)
    if norm < 1e-15:
        raise ValueError("Cannot normalize zero vector")
    return state / norm


def random_state(n_qubits: int, seed: Optional[int] = None) -> np.ndarray:
    """Generate a random normalized state vector."""
    if seed is not None:
        np.random.seed(seed)

    dim = 2 ** n_qubits
    real = np.random.randn(dim)
    imag = np.random.randn(dim)
    state = real + 1j * imag
    return normalize_state(state)


def random_unitary(n: int, seed: Optional[int] = None) -> np.ndarray:
    """Generate a Haar-random unitary matrix via QR decomposition."""
    if seed is not None:
        np.random.seed(seed)

    # Generate random complex matrix
    real = np.random.randn(n, n)
    imag = np.random.randn(n, n)
    A = real + 1j * imag

    # QR decomposition gives unitary Q
    Q, R = np.linalg.qr(A)

    # Make it Haar random by fixing phases
    d = np.diag(R)
    ph = d / np.abs(d)
    Q = Q @ np.diag(ph)

    return Q


def matrix_exponential(A: np.ndarray) -> np.ndarray:
    """
    Compute matrix exponential e^A.
    """
    from scipy.linalg import expm
    return expm(A)


def matrix_logarithm(A: np.ndarray) -> np.ndarray:
    """
    Compute matrix logarithm log(A).
    """
    from scipy.linalg import logm
    return logm(A)
