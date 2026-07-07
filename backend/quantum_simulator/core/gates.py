"""Quantum gate matrices."""

import numpy as np
from typing import List, Optional
from functools import reduce

# Type alias for gate matrices
GateMatrix = np.ndarray

# Identity gate
I: GateMatrix = np.array([
    [1, 0],
    [0, 1]
], dtype=complex)

# Pauli-X (NOT gate)
X: GateMatrix = np.array([
    [0, 1],
    [1, 0]
], dtype=complex)

# Pauli-Y
Y: GateMatrix = np.array([
    [0, -1j],
    [1j, 0]
], dtype=complex)

# Pauli-Z
Z: GateMatrix = np.array([
    [1, 0],
    [0, -1]
], dtype=complex)

# Hadamard gate
H: GateMatrix = np.array([
    [1, 1],
    [1, -1]
], dtype=complex) / np.sqrt(2)

# S gate (sqrt(Z), phase gate)
S: GateMatrix = np.array([
    [1, 0],
    [0, 1j]
], dtype=complex)

# S-dagger (S inverse)
Sdg: GateMatrix = np.array([
    [1, 0],
    [0, -1j]
], dtype=complex)

# T gate (sqrt(S), pi/8 gate)
T: GateMatrix = np.array([
    [1, 0],
    [0, np.exp(1j * np.pi / 4)]
], dtype=complex)

# T-dagger (T inverse)
Tdg: GateMatrix = np.array([
    [1, 0],
    [0, np.exp(-1j * np.pi / 4)]
], dtype=complex)

# Square root of X (sqrt(X))
SX: GateMatrix = np.array([
    [1 + 1j, 1 - 1j],
    [1 - 1j, 1 + 1j]
], dtype=complex) / 2

# Square root of X dagger
SXdg: GateMatrix = np.array([
    [1 - 1j, 1 + 1j],
    [1 + 1j, 1 - 1j]
], dtype=complex) / 2


def Rx(theta: float) -> GateMatrix:
    """Rotation around X-axis by angle theta."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, -1j * s],
        [-1j * s, c]
    ], dtype=complex)


def Ry(theta: float) -> GateMatrix:
    """Rotation around Y-axis by angle theta."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, -s],
        [s, c]
    ], dtype=complex)


def Rz(theta: float) -> GateMatrix:
    """Rotation around Z-axis by angle theta."""
    return np.array([
        [np.exp(-1j * theta / 2), 0],
        [0, np.exp(1j * theta / 2)]
    ], dtype=complex)


def Phase(theta: float) -> GateMatrix:
    """Phase gate P(theta) = diag(1, e^(i*theta))."""
    return np.array([
        [1, 0],
        [0, np.exp(1j * theta)]
    ], dtype=complex)


def U1(lam: float) -> GateMatrix:
    """U1 gate (equivalent to Phase gate)."""
    return Phase(lam)


def U2(phi: float, lam: float) -> GateMatrix:
    """U2 gate: 1/sqrt(2) * [[1, -e^(i*lam)], [e^(i*phi), e^(i*(phi+lam))]]."""
    return np.array([
        [1, -np.exp(1j * lam)],
        [np.exp(1j * phi), np.exp(1j * (phi + lam))]
    ], dtype=complex) / np.sqrt(2)


def U3(theta: float, phi: float, lam: float) -> GateMatrix:
    """
    Universal single-qubit gate U3(theta, phi, lambda).
    U3 = [[cos(θ/2), -e^(iλ)sin(θ/2)],
          [e^(iφ)sin(θ/2), e^(i(φ+λ))cos(θ/2)]]
    """
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, -np.exp(1j * lam) * s],
        [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]
    ], dtype=complex)


def U(theta: float, phi: float, lam: float, gamma: float = 0) -> GateMatrix:
    """General unitary gate with global phase."""
    return np.exp(1j * gamma) * U3(theta, phi, lam)


# CNOT (CX) gate - control on qubit 0, target on qubit 1
CNOT: GateMatrix = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1],
    [0, 0, 1, 0]
], dtype=complex)

CX: GateMatrix = CNOT  # Alias

# CY gate
CY: GateMatrix = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 0, -1j],
    [0, 0, 1j, 0]
], dtype=complex)

# CZ gate (controlled-Z)
CZ: GateMatrix = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, -1]
], dtype=complex)

# SWAP gate
SWAP: GateMatrix = np.array([
    [1, 0, 0, 0],
    [0, 0, 1, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1]
], dtype=complex)

# iSWAP gate
iSWAP: GateMatrix = np.array([
    [1, 0, 0, 0],
    [0, 0, 1j, 0],
    [0, 1j, 0, 0],
    [0, 0, 0, 1]
], dtype=complex)

# Square root of SWAP
SQSWAP: GateMatrix = np.array([
    [1, 0, 0, 0],
    [0, 0.5 * (1 + 1j), 0.5 * (1 - 1j), 0],
    [0, 0.5 * (1 - 1j), 0.5 * (1 + 1j), 0],
    [0, 0, 0, 1]
], dtype=complex)

# Square root of iSWAP
SQiSWAP: GateMatrix = np.array([
    [1, 0, 0, 0],
    [0, 1 / np.sqrt(2), 1j / np.sqrt(2), 0],
    [0, 1j / np.sqrt(2), 1 / np.sqrt(2), 0],
    [0, 0, 0, 1]
], dtype=complex)


def CRx(theta: float) -> GateMatrix:
    """Controlled rotation around X-axis."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, c, -1j * s],
        [0, 0, -1j * s, c]
    ], dtype=complex)


def CRy(theta: float) -> GateMatrix:
    """Controlled rotation around Y-axis."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, c, -s],
        [0, 0, s, c]
    ], dtype=complex)


def CRz(theta: float) -> GateMatrix:
    """Controlled rotation around Z-axis."""
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, np.exp(-1j * theta / 2), 0],
        [0, 0, 0, np.exp(1j * theta / 2)]
    ], dtype=complex)


def CPhase(theta: float) -> GateMatrix:
    """Controlled phase gate."""
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, np.exp(1j * theta)]
    ], dtype=complex)


def CU(theta: float, phi: float, lam: float, gamma: float = 0) -> GateMatrix:
    """Controlled-U gate."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    phase = np.exp(1j * gamma)
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, phase * c, -phase * np.exp(1j * lam) * s],
        [0, 0, phase * np.exp(1j * phi) * s, phase * np.exp(1j * (phi + lam)) * c]
    ], dtype=complex)


def Rxx(theta: float) -> GateMatrix:
    """Two-qubit XX rotation (Ising coupling)."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, 0, 0, -1j * s],
        [0, c, -1j * s, 0],
        [0, -1j * s, c, 0],
        [-1j * s, 0, 0, c]
    ], dtype=complex)


def Ryy(theta: float) -> GateMatrix:
    """Two-qubit YY rotation (Ising coupling)."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, 0, 0, 1j * s],
        [0, c, -1j * s, 0],
        [0, -1j * s, c, 0],
        [1j * s, 0, 0, c]
    ], dtype=complex)


def Rzz(theta: float) -> GateMatrix:
    """Two-qubit ZZ rotation (Ising coupling)."""
    return np.array([
        [np.exp(-1j * theta / 2), 0, 0, 0],
        [0, np.exp(1j * theta / 2), 0, 0],
        [0, 0, np.exp(1j * theta / 2), 0],
        [0, 0, 0, np.exp(-1j * theta / 2)]
    ], dtype=complex)


# Toffoli gate (CCNOT)
TOFFOLI: GateMatrix = np.array([
    [1, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 1, 0]
], dtype=complex)

CCNOT: GateMatrix = TOFFOLI  # Alias
CCX: GateMatrix = TOFFOLI  # Alias

# Fredkin gate (CSWAP)
FREDKIN: GateMatrix = np.array([
    [1, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1]
], dtype=complex)

CSWAP: GateMatrix = FREDKIN  # Alias


def CCZ() -> GateMatrix:
    """Controlled-controlled-Z gate."""
    ccz = np.eye(8, dtype=complex)
    ccz[7, 7] = -1
    return ccz


def controlled(gate: GateMatrix, n_controls: int = 1) -> GateMatrix:
    """Create a controlled version of a gate."""
    gate_size = gate.shape[0]
    n_target_qubits = int(np.log2(gate_size))
    total_qubits = n_controls + n_target_qubits
    size = 2 ** total_qubits

    # Start with identity
    controlled_gate = np.eye(size, dtype=complex)

    # The gate is applied only when all control qubits are |1⟩
    # This corresponds to the bottom-right block of size gate_size
    start_idx = size - gate_size
    controlled_gate[start_idx:, start_idx:] = gate

    return controlled_gate


def tensor_gate(gate: GateMatrix, qubit: int, n_qubits: int) -> GateMatrix:
    """Expand a single-qubit gate to act on a specific qubit in an n-qubit system."""
    if n_qubits == 1:
        return gate

    ops = [I] * n_qubits
    ops[n_qubits - 1 - qubit] = gate  # Reverse indexing for standard convention

    result = ops[0]
    for op in ops[1:]:
        result = np.kron(result, op)

    return result


def multi_qubit_gate(gate: GateMatrix, qubits: List[int], n_qubits: int) -> GateMatrix:
    """Expand a multi-qubit gate to act on specific qubits in an n-qubit system.

    Convention: qubits[0] is the most-significant bit of the gate index, so a
    two-qubit controlled gate applied to [control, target] matches its textbook
    matrix. The state uses little-endian order (qubit q -> bit (i >> q) & 1).
    """
    n_gate_qubits = len(qubits)
    gate_dim = 2 ** n_gate_qubits
    total_dim = 2 ** n_qubits

    if gate.shape != (gate_dim, gate_dim):
        raise ValueError(f"Gate shape {gate.shape} doesn't match {n_gate_qubits} qubits")

    other_qubits = [q for q in range(n_qubits) if q not in qubits]

    result = np.zeros((total_dim, total_dim), dtype=complex)

    for i in range(total_dim):
        for j in range(total_dim):
            i_bits = [(i >> q) & 1 for q in range(n_qubits)]
            j_bits = [(j >> q) & 1 for q in range(n_qubits)]

            # qubits[0] is the highest gate-index bit
            i_gate = sum(i_bits[qubits[k]] << (n_gate_qubits - 1 - k) for k in range(n_gate_qubits))
            j_gate = sum(j_bits[qubits[k]] << (n_gate_qubits - 1 - k) for k in range(n_gate_qubits))

            i_other = [i_bits[q] for q in other_qubits]
            j_other = [j_bits[q] for q in other_qubits]

            if i_other == j_other:
                result[i, j] = gate[i_gate, j_gate]

    return result


def apply_gate_to_statevector(amplitudes: np.ndarray, gate: GateMatrix,
                              qubits: List[int], n_qubits: int) -> np.ndarray:
    """Apply a gate to a state vector by tensor contraction.

    Reshapes the 2^n amplitude vector into an n-dimensional tensor and contracts
    only the gate's axes, which is O(2^n * 2^m) for an m-qubit gate rather than
    the O(4^n) of building a full 2^n x 2^n matrix. Uses the same convention as
    multi_qubit_gate: qubits[0] is the most-significant gate-index bit and the
    state is little-endian (state axis for qubit q is n_qubits - 1 - q).
    """
    m = len(qubits)
    psi = amplitudes.reshape([2] * n_qubits)
    g = gate.reshape([2] * (2 * m))

    state_axes = [n_qubits - 1 - q for q in qubits]
    # Contract the gate's input axes (m..2m-1) with the corresponding state axes.
    psi = np.tensordot(g, psi, axes=(list(range(m, 2 * m)), state_axes))

    # tensordot leaves the gate's output axes (one per qubit, in order) first,
    # followed by the untouched state axes in ascending order. Move each output
    # axis back to the state position of its qubit.
    remaining = [a for a in range(n_qubits) if a not in state_axes]
    source = {}
    for k, a in enumerate(state_axes):
        source[a] = k
    for idx, a in enumerate(remaining):
        source[a] = m + idx
    perm = [source[a] for a in range(n_qubits)]

    psi = np.transpose(psi, perm)
    return psi.reshape(-1)


def is_unitary(gate: GateMatrix, tol: float = 1e-10) -> bool:
    """Check if a gate matrix is unitary."""
    n = gate.shape[0]
    product = gate @ gate.conj().T
    return np.allclose(product, np.eye(n), atol=tol)


def gate_fidelity(gate1: GateMatrix, gate2: GateMatrix) -> float:
    """
    Calculate the fidelity between two gates.
    F = |Tr(U1† U2)|² / d²
    """
    d = gate1.shape[0]
    trace = np.trace(gate1.conj().T @ gate2)
    return (np.abs(trace) ** 2) / (d ** 2)


SINGLE_QUBIT_GATES = {
    'I': I, 'X': X, 'Y': Y, 'Z': Z,
    'H': H, 'S': S, 'Sdg': Sdg, 'T': T, 'Tdg': Tdg,
    'SX': SX, 'SXdg': SXdg,
}

TWO_QUBIT_GATES = {
    'CNOT': CNOT, 'CX': CX, 'CY': CY, 'CZ': CZ,
    'SWAP': SWAP, 'iSWAP': iSWAP, 'SQSWAP': SQSWAP,
}

THREE_QUBIT_GATES = {
    'TOFFOLI': TOFFOLI, 'CCNOT': CCNOT, 'CCX': CCX,
    'FREDKIN': FREDKIN, 'CSWAP': CSWAP,
}

PARAMETERIZED_GATES = {
    'Rx': Rx, 'Ry': Ry, 'Rz': Rz,
    'Phase': Phase, 'U1': U1, 'U2': U2, 'U3': U3, 'U': U,
    'CRx': CRx, 'CRy': CRy, 'CRz': CRz, 'CPhase': CPhase, 'CU': CU,
    'Rxx': Rxx, 'Ryy': Ryy, 'Rzz': Rzz,
}


def get_gate(name: str, params: Optional[List[float]] = None) -> GateMatrix:
    """Look up a gate matrix by name, with optional parameters."""
    # Check single-qubit gates
    if name in SINGLE_QUBIT_GATES:
        return SINGLE_QUBIT_GATES[name]

    # Check two-qubit gates
    if name in TWO_QUBIT_GATES:
        return TWO_QUBIT_GATES[name]

    # Check three-qubit gates
    if name in THREE_QUBIT_GATES:
        return THREE_QUBIT_GATES[name]

    # Check parameterized gates
    if name in PARAMETERIZED_GATES:
        if params is None:
            raise ValueError(f"Gate '{name}' requires parameters")
        return PARAMETERIZED_GATES[name](*params)

    raise ValueError(f"Unknown gate: {name}")
