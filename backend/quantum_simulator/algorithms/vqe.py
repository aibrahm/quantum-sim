"""
Variational Quantum Eigensolver (VQE).

Reference: Peruzzo et al., Nature Communications 5, 4213 (2014), arXiv:1304.3061
"""

import numpy as np
from typing import List, Optional, Tuple, Dict, Any, Callable
from dataclasses import dataclass, field
from scipy.optimize import minimize

from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import get_statevector
from ..core.state_vector import StateVector


@dataclass
class PauliTerm:
    """A single term in a Pauli Hamiltonian: coefficient * tensor product of Pauli operators."""
    coefficient: float
    paulis: str  # e.g. "XZIY" means X⊗Z⊗I⊗Y

    def to_matrix(self) -> np.ndarray:
        """Convert to matrix representation."""
        pauli_matrices = {
            'I': np.eye(2, dtype=complex),
            'X': np.array([[0, 1], [1, 0]], dtype=complex),
            'Y': np.array([[0, -1j], [1j, 0]], dtype=complex),
            'Z': np.array([[1, 0], [0, -1]], dtype=complex),
        }
        result = np.array([[1]], dtype=complex)
        for p in self.paulis:
            result = np.kron(result, pauli_matrices[p])
        return self.coefficient * result


@dataclass
class PauliHamiltonian:
    """Hamiltonian as a sum of Pauli terms: H = Σᵢ cᵢ Pᵢ."""
    terms: List[PauliTerm]
    n_qubits: int

    def to_matrix(self) -> np.ndarray:
        """Convert to full matrix representation."""
        dim = 2 ** self.n_qubits
        H = np.zeros((dim, dim), dtype=complex)
        for term in self.terms:
            H += term.to_matrix()
        return H

    def exact_ground_energy(self) -> float:
        """Compute exact ground state energy by diagonalization."""
        H = self.to_matrix()
        eigenvalues = np.linalg.eigvalsh(H)
        return float(eigenvalues[0])

    @classmethod
    def h2_hamiltonian(cls, bond_length: float = 0.735) -> 'PauliHamiltonian':
        """Simplified H2 molecule Hamiltonian in STO-3G basis."""
        # Coefficients from Bravyi-Kitaev transformation at given bond length
        g0 = -0.4804 + 0.3435 * (bond_length - 0.735)
        g1 = 0.3435 - 0.0946 * (bond_length - 0.735)
        g2 = -0.4347 + 0.1231 * (bond_length - 0.735)
        g3 = 0.0910 + 0.0462 * (bond_length - 0.735)
        g4 = 0.0910 + 0.0462 * (bond_length - 0.735)
        g5 = 0.1712 - 0.0551 * (bond_length - 0.735)

        terms = [
            PauliTerm(g0, "II"),
            PauliTerm(g1, "IZ"),
            PauliTerm(g2, "ZI"),
            PauliTerm(g3, "ZZ"),
            PauliTerm(g4, "XX"),
            PauliTerm(g5, "YY"),
        ]
        return cls(terms=terms, n_qubits=2)

    @classmethod
    def transverse_ising(cls, n_qubits: int, J: float = 1.0, h: float = 0.5) -> 'PauliHamiltonian':
        """Transverse-field Ising model: H = -J Σᵢ ZᵢZᵢ₊₁ - h Σᵢ Xᵢ."""
        terms = []

        # ZZ interactions
        for i in range(n_qubits - 1):
            paulis = ['I'] * n_qubits
            paulis[i] = 'Z'
            paulis[i + 1] = 'Z'
            terms.append(PauliTerm(-J, ''.join(paulis)))

        # Transverse field
        for i in range(n_qubits):
            paulis = ['I'] * n_qubits
            paulis[i] = 'X'
            terms.append(PauliTerm(-h, ''.join(paulis)))

        return cls(terms=terms, n_qubits=n_qubits)


def hardware_efficient_ansatz(
    n_qubits: int,
    depth: int = 2,
    params: Optional[List[float]] = None
) -> Tuple[QuantumCircuit, int]:
    """Hardware-efficient ansatz with Ry/Rz layers and CX entanglement."""
    n_params = 2 * n_qubits * depth + 2 * n_qubits
    if params is None:
        params = [0.0] * n_params

    qc = QuantumCircuit(n_qubits, name="hw_efficient_ansatz")
    param_idx = 0

    for layer in range(depth):
        for q in range(n_qubits):
            qc.ry(params[param_idx], q)
            param_idx += 1

        for q in range(n_qubits):
            qc.rz(params[param_idx], q)
            param_idx += 1

        for q in range(n_qubits - 1):
            qc.cx(q, q + 1)

    for q in range(n_qubits):
        qc.ry(params[param_idx], q)
        param_idx += 1
    for q in range(n_qubits):
        qc.rz(params[param_idx], q)
        param_idx += 1

    return qc, n_params


def uccsd_ansatz(
    n_qubits: int = 4,
    n_electrons: int = 2,
    params: Optional[List[float]] = None
) -> Tuple[QuantumCircuit, int]:
    """UCCSD ansatz. For 2-qubit H2, reduces to a single Ry rotation."""
    if n_qubits == 2:
        n_params = 1
        if params is None:
            params = [0.0]

        qc = QuantumCircuit(2, name="uccsd_h2")
        qc.x(0)
        qc.ry(params[0], 1)
        qc.cx(1, 0)

        return qc, n_params

    n_occupied = n_electrons
    n_virtual = n_qubits - n_electrons

    n_singles = n_occupied * n_virtual
    n_doubles = n_singles * (n_singles - 1) // 2
    n_params = n_singles + n_doubles

    if params is None:
        params = [0.0] * n_params

    qc = QuantumCircuit(n_qubits, name="uccsd")

    for i in range(n_electrons):
        qc.x(i)

    param_idx = 0

    for i in range(n_occupied):
        for a in range(n_occupied, n_qubits):
            theta = params[param_idx]
            param_idx += 1

            qc.ry(theta / 2, a)
            qc.cx(a, i)
            qc.ry(-theta / 2, a)
            qc.cx(a, i)

    for i in range(n_occupied):
        for j in range(i + 1, n_occupied):
            for a in range(n_occupied, n_qubits):
                for b in range(a + 1, n_qubits):
                    if param_idx >= n_params:
                        break
                    theta = params[param_idx]
                    param_idx += 1

                    qc.cx(i, a)
                    qc.cx(j, b)
                    qc.ry(theta, a)
                    qc.cx(b, a)
                    qc.ry(-theta, a)
                    qc.cx(b, a)
                    qc.cx(j, b)
                    qc.cx(i, a)

    return qc, n_params


@dataclass
class VQEResult:
    """Result of a VQE optimization run."""
    ground_energy: float
    optimal_params: List[float]
    convergence_history: List[float]
    iterations: int
    exact_energy: Optional[float] = None
    chemical_accuracy: bool = False  # < 1.6 mHa error
    ansatz: str = ""
    hamiltonian: str = ""


def measure_expectation(
    hamiltonian: PauliHamiltonian,
    circuit: QuantumCircuit
) -> float:
    """Measure <psi|H|psi> for a Pauli Hamiltonian."""
    sv = get_statevector(circuit)
    psi = sv.amplitudes

    H_matrix = hamiltonian.to_matrix()
    expectation = np.real(psi.conj() @ H_matrix @ psi)

    return float(expectation)


def run_vqe(
    hamiltonian: PauliHamiltonian,
    ansatz_type: str = "hardware_efficient",
    ansatz_depth: int = 2,
    initial_params: Optional[List[float]] = None,
    optimizer: str = "COBYLA",
    max_iterations: int = 200,
    tol: float = 1e-6
) -> VQEResult:
    """Run VQE to find the ground state energy of a Hamiltonian."""
    n_qubits = hamiltonian.n_qubits
    convergence_history = []

    if ansatz_type == "uccsd":
        _, n_params = uccsd_ansatz(n_qubits)
    else:
        _, n_params = hardware_efficient_ansatz(n_qubits, ansatz_depth)

    if initial_params is None:
        np.random.seed(42)
        initial_params = np.random.uniform(-np.pi, np.pi, n_params).tolist()

    def cost_function(params):
        if ansatz_type == "uccsd":
            circuit, _ = uccsd_ansatz(n_qubits, params=params.tolist())
        else:
            circuit, _ = hardware_efficient_ansatz(n_qubits, ansatz_depth, params.tolist())

        energy = measure_expectation(hamiltonian, circuit)
        convergence_history.append(energy)
        return energy

    result = minimize(
        cost_function,
        np.array(initial_params),
        method=optimizer,
        options={'maxiter': max_iterations, 'rhobeg': 0.5},
        tol=tol
    )

    exact_energy = hamiltonian.exact_ground_energy()
    error_ha = abs(result.fun - exact_energy)
    chemical_accuracy = error_ha < 0.0016  # 1.6 milliHartree

    return VQEResult(
        ground_energy=float(result.fun),
        optimal_params=result.x.tolist(),
        convergence_history=convergence_history,
        iterations=len(convergence_history),
        exact_energy=exact_energy,
        chemical_accuracy=chemical_accuracy,
        ansatz=ansatz_type,
        hamiltonian=f"{len(hamiltonian.terms)}-term Pauli Hamiltonian on {n_qubits} qubits"
    )


def run_h2_vqe(
    bond_length: float = 0.735,
    ansatz_type: str = "uccsd",
    max_iterations: int = 200
) -> VQEResult:
    """Run VQE for H2 molecule."""
    H = PauliHamiltonian.h2_hamiltonian(bond_length)
    return run_vqe(H, ansatz_type=ansatz_type, max_iterations=max_iterations)
