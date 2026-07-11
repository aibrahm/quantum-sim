"""
DensityMatrix - Mixed quantum state representation.
Implements density operator ρ for both pure and mixed states.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Union
from dataclasses import dataclass

from .gates import GateMatrix, multi_qubit_gate, tensor_gate, apply_gate_to_statevector, I
from .utils import (
    tensor_product, partial_trace_simple, state_to_bloch,
    is_hermitian, is_positive_semidefinite
)


@dataclass
class DensityMeasurementResult:
    """Result of measuring a density matrix."""
    outcome: int
    outcome_bits: str
    probability: float
    post_state: Optional['DensityMatrix'] = None


class DensityMatrix:
    """
    Density matrix representation of a quantum state.

    The density operator ρ satisfies:
    1. Hermitian: ρ = ρ†
    2. Positive semidefinite: ⟨ψ|ρ|ψ⟩ ≥ 0 for all |ψ⟩
    3. Unit trace: Tr(ρ) = 1

    For pure states: ρ = |ψ⟩⟨ψ|
    For mixed states: ρ = Σᵢ pᵢ |ψᵢ⟩⟨ψᵢ|
    """

    MAX_QUBITS = 14  # Lower than StateVector due to O(4^n) memory

    def __init__(self, n_qubits: int, rho: Optional[np.ndarray] = None):
        """
        Initialize a density matrix.

        Args:
            n_qubits: Number of qubits
            rho: Optional density matrix (defaults to |0...0⟩⟨0...0|)
        """
        if n_qubits < 1:
            raise ValueError("Number of qubits must be at least 1")
        if n_qubits > self.MAX_QUBITS:
            raise ValueError(f"Maximum {self.MAX_QUBITS} qubits for density matrix")

        self._n_qubits = n_qubits
        self._dim = 2 ** n_qubits

        if rho is not None:
            if rho.shape != (self._dim, self._dim):
                raise ValueError(f"Density matrix must have shape ({self._dim}, {self._dim})")
            self._rho = rho.astype(complex)
            # Normalize trace to 1
            trace = np.trace(self._rho)
            if np.abs(trace) > 1e-15:
                self._rho /= trace
        else:
            # Initialize to |0...0⟩⟨0...0|
            self._rho = np.zeros((self._dim, self._dim), dtype=complex)
            self._rho[0, 0] = 1.0

    @classmethod
    def from_state_vector(cls, state: np.ndarray) -> 'DensityMatrix':
        """
        Create density matrix from a pure state vector.

        Args:
            state: State vector |ψ⟩

        Returns:
            DensityMatrix ρ = |ψ⟩⟨ψ|
        """
        state = np.asarray(state, dtype=complex).flatten()
        dim = len(state)
        n_qubits = int(np.log2(dim))

        if 2 ** n_qubits != dim:
            raise ValueError("State vector dimension must be a power of 2")

        # Normalize
        state = state / np.linalg.norm(state)
        rho = np.outer(state, np.conj(state))

        return cls(n_qubits, rho)

    @classmethod
    def from_ensemble(cls, states: List[np.ndarray], probabilities: List[float]) -> 'DensityMatrix':
        """
        Create density matrix from a statistical ensemble.

        Args:
            states: List of state vectors
            probabilities: Classical probabilities for each state

        Returns:
            DensityMatrix ρ = Σᵢ pᵢ |ψᵢ⟩⟨ψᵢ|
        """
        if len(states) != len(probabilities):
            raise ValueError("Number of states must match number of probabilities")

        if not np.isclose(sum(probabilities), 1.0):
            raise ValueError("Probabilities must sum to 1")

        dim = len(states[0])
        n_qubits = int(np.log2(dim))

        rho = np.zeros((dim, dim), dtype=complex)
        for state, prob in zip(states, probabilities):
            state = np.asarray(state, dtype=complex).flatten()
            state = state / np.linalg.norm(state)
            rho += prob * np.outer(state, np.conj(state))

        return cls(n_qubits, rho)

    @classmethod
    def maximally_mixed(cls, n_qubits: int) -> 'DensityMatrix':
        """
        Create maximally mixed state ρ = I/d.

        Args:
            n_qubits: Number of qubits

        Returns:
            Maximally mixed density matrix
        """
        dim = 2 ** n_qubits
        rho = np.eye(dim, dtype=complex) / dim
        return cls(n_qubits, rho)

    @classmethod
    def thermal_state(cls, hamiltonian: np.ndarray, temperature: float) -> 'DensityMatrix':
        """
        Create thermal (Gibbs) state ρ = e^(-H/kT) / Z.

        Args:
            hamiltonian: Hamiltonian matrix
            temperature: Temperature (in energy units, kB=1)

        Returns:
            Thermal density matrix
        """
        dim = hamiltonian.shape[0]
        n_qubits = int(np.log2(dim))

        if temperature <= 0:
            # Ground state in zero temperature limit
            eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
            ground_state = eigenvectors[:, 0]
            return cls.from_state_vector(ground_state)

        beta = 1.0 / temperature
        exp_H = np.diag(np.exp(-beta * np.linalg.eigvalsh(hamiltonian)))

        # Diagonalize H
        eigenvalues, U = np.linalg.eigh(hamiltonian)
        rho_diag = np.diag(np.exp(-beta * eigenvalues))
        rho = U @ rho_diag @ U.conj().T

        # Normalize
        rho /= np.trace(rho)

        return cls(n_qubits, rho)

    @property
    def n_qubits(self) -> int:
        return self._n_qubits

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def rho(self) -> np.ndarray:
        """Density matrix (read-only copy)."""
        return self._rho.copy()

    @property
    def matrix(self) -> np.ndarray:
        """Alias for rho property."""
        return self._rho.copy()

    def _conjugate_by(self, op: np.ndarray, qubits: List[int]) -> np.ndarray:
        """Compute op ρ op† by tensor contraction, without building a 2^n x 2^n operator.

        The flattened ρ is a 2n-qubit vector where column qubit q is overall
        qubit q and row qubit q is overall qubit q + n, so op contracts the row
        axes (op ρ) and conj(op) contracts the column axes (ρ op†). This mirrors
        the state-vector kernel and keeps gate application O(4^n * 2^m) instead
        of O(4^n) operator construction plus dense matmuls.
        """
        n = self._n_qubits
        flat = self._rho.reshape(-1)
        flat = apply_gate_to_statevector(flat, op, [q + n for q in qubits], 2 * n)
        flat = apply_gate_to_statevector(flat, op.conj(), list(qubits), 2 * n)
        return flat.reshape(self._dim, self._dim)

    def apply_gate(self, gate: GateMatrix, qubits: List[int]) -> 'DensityMatrix':
        """
        Apply unitary gate: ρ → U ρ U†.

        Args:
            gate: Unitary gate matrix
            qubits: Qubit indices

        Returns:
            New DensityMatrix after gate
        """
        for q in qubits:
            if q < 0 or q >= self._n_qubits:
                raise ValueError(f"Qubit {q} out of range")

        new_rho = self._conjugate_by(gate, qubits)

        return DensityMatrix(self._n_qubits, new_rho)

    def apply_gate_inplace(self, gate: GateMatrix, qubits: List[int]) -> None:
        """Apply gate in place."""
        for q in qubits:
            if q < 0 or q >= self._n_qubits:
                raise ValueError(f"Qubit {q} out of range")

        self._rho = self._conjugate_by(gate, qubits)

    def apply_channel(self, kraus_ops: List[np.ndarray], qubits: List[int]) -> 'DensityMatrix':
        """
        Apply quantum channel with Kraus operators: ρ → Σᵢ Kᵢ ρ Kᵢ†.

        Args:
            kraus_ops: List of Kraus operators
            qubits: Qubits the channel acts on

        Returns:
            New DensityMatrix after channel
        """
        new_rho = np.zeros_like(self._rho)

        for K in kraus_ops:
            new_rho += self._conjugate_by(K, qubits)

        return DensityMatrix(self._n_qubits, new_rho)

    def apply_channel_inplace(self, kraus_ops: List[np.ndarray], qubits: List[int]) -> None:
        """Apply channel in place."""
        new_rho = np.zeros_like(self._rho)

        for K in kraus_ops:
            new_rho += self._conjugate_by(K, qubits)

        self._rho = new_rho

    def measure(self, qubits: Optional[List[int]] = None) -> DensityMeasurementResult:
        """
        Perform projective measurement.

        Args:
            qubits: Qubits to measure (None = all)

        Returns:
            Measurement result with outcome and post-measurement state
        """
        if qubits is None:
            qubits = list(range(self._n_qubits))

        n_measured = len(qubits)

        # Calculate outcome probabilities
        outcome_probs = np.zeros(2 ** n_measured)

        for outcome in range(2 ** n_measured):
            # Build projector for this outcome
            projector = np.zeros((self._dim, self._dim), dtype=complex)

            for i in range(self._dim):
                # Check if basis state i matches the outcome on measured qubits
                match = True
                for k, q in enumerate(qubits):
                    bit = (i >> q) & 1
                    expected = (outcome >> k) & 1
                    if bit != expected:
                        match = False
                        break

                if match:
                    projector[i, i] = 1.0

            outcome_probs[outcome] = np.real(np.trace(projector @ self._rho))

        # Normalize probabilities
        outcome_probs = np.maximum(outcome_probs, 0)  # Numerical stability
        outcome_probs /= np.sum(outcome_probs)

        # Sample outcome
        outcome = np.random.choice(2 ** n_measured, p=outcome_probs)
        outcome_bits = format(outcome, f'0{n_measured}b')

        # Build projector for sampled outcome
        projector = np.zeros((self._dim, self._dim), dtype=complex)
        for i in range(self._dim):
            match = True
            for k, q in enumerate(qubits):
                bit = (i >> q) & 1
                expected = (outcome >> k) & 1
                if bit != expected:
                    match = False
                    break
            if match:
                projector[i, i] = 1.0

        # Collapse: ρ → P ρ P / Tr(P ρ)
        new_rho = projector @ self._rho @ projector
        trace = np.trace(new_rho)
        if np.abs(trace) > 1e-15:
            new_rho /= trace

        return DensityMeasurementResult(
            outcome=outcome,
            outcome_bits=outcome_bits,
            probability=outcome_probs[outcome],
            post_state=DensityMatrix(self._n_qubits, new_rho)
        )

    def sample(self, shots: int = 1024, qubits: Optional[List[int]] = None) -> Dict[str, int]:
        """
        Sample measurement outcomes.

        Args:
            shots: Number of measurements
            qubits: Qubits to measure (None = all)

        Returns:
            Counts dictionary
        """
        if qubits is None:
            qubits = list(range(self._n_qubits))

        n_measured = len(qubits)

        # Calculate probabilities
        outcome_probs = np.zeros(2 ** n_measured)

        for outcome in range(2 ** n_measured):
            for i in range(self._dim):
                match = True
                for k, q in enumerate(qubits):
                    bit = (i >> q) & 1
                    expected = (outcome >> k) & 1
                    if bit != expected:
                        match = False
                        break
                if match:
                    outcome_probs[outcome] += np.real(self._rho[i, i])

        # Normalize
        outcome_probs = np.maximum(outcome_probs, 0)
        outcome_probs /= np.sum(outcome_probs)

        # Sample
        outcomes = np.random.choice(2 ** n_measured, size=shots, p=outcome_probs)

        counts: Dict[str, int] = {}
        for outcome in outcomes:
            key = format(outcome, f'0{n_measured}b')
            counts[key] = counts.get(key, 0) + 1

        return counts

    def partial_trace(self, keep_qubits: List[int]) -> 'DensityMatrix':
        """
        Compute partial trace, keeping specified qubits.

        Args:
            keep_qubits: Qubits to keep

        Returns:
            Reduced density matrix
        """
        trace_out = [q for q in range(self._n_qubits) if q not in keep_qubits]
        reduced_rho = partial_trace_simple(self._rho, trace_out, self._n_qubits)
        return DensityMatrix(len(keep_qubits), reduced_rho)

    def expectation(self, observable: np.ndarray, qubits: Optional[List[int]] = None) -> float:
        """
        Calculate expectation value Tr(ρ O).

        Args:
            observable: Hermitian operator
            qubits: Qubits observable acts on

        Returns:
            Real expectation value
        """
        if qubits is not None:
            observable = multi_qubit_gate(observable, qubits, self._n_qubits)

        return float(np.real(np.trace(self._rho @ observable)))

    def purity(self) -> float:
        """
        Calculate purity Tr(ρ²).

        Returns 1 for pure states, 1/d for maximally mixed.
        """
        return float(np.real(np.trace(self._rho @ self._rho)))

    def is_pure(self, tol: float = 1e-10) -> bool:
        """Check if state is pure (purity ≈ 1)."""
        return np.abs(self.purity() - 1.0) < tol

    def von_neumann_entropy(self, base: float = 2) -> float:
        """
        Calculate von Neumann entropy S = -Tr(ρ log ρ).

        Args:
            base: Logarithm base (2 for bits, e for nats)

        Returns:
            Entropy value
        """
        eigenvalues = np.linalg.eigvalsh(self._rho)
        eigenvalues = eigenvalues[eigenvalues > 1e-15]  # Filter near-zero

        if base == 2:
            return float(-np.sum(eigenvalues * np.log2(eigenvalues)))
        elif base == np.e:
            return float(-np.sum(eigenvalues * np.log(eigenvalues)))
        else:
            return float(-np.sum(eigenvalues * np.log(eigenvalues) / np.log(base)))

    def linear_entropy(self) -> float:
        """
        Calculate linear entropy S_L = 1 - Tr(ρ²).

        Simpler alternative to von Neumann entropy.
        """
        return 1.0 - self.purity()

    def fidelity(self, other: Union['DensityMatrix', np.ndarray]) -> float:
        """
        Calculate fidelity F(ρ, σ) = (Tr√(√ρ σ √ρ))².

        Args:
            other: Another density matrix

        Returns:
            Fidelity in [0, 1]
        """
        if isinstance(other, DensityMatrix):
            sigma = other._rho
        else:
            sigma = other

        # For pure state σ = |ψ⟩⟨ψ|: F = ⟨ψ|ρ|ψ⟩
        if np.allclose(sigma @ sigma, sigma):  # Check if pure
            return float(np.real(np.trace(self._rho @ sigma)))

        # General case using matrix square root
        from scipy.linalg import sqrtm
        sqrt_rho = sqrtm(self._rho)
        inner = sqrtm(sqrt_rho @ sigma @ sqrt_rho)
        return float(np.real(np.trace(inner)) ** 2)

    def trace_distance(self, other: 'DensityMatrix') -> float:
        """
        Calculate trace distance D(ρ, σ) = ½ ||ρ - σ||₁.

        Args:
            other: Another density matrix

        Returns:
            Trace distance in [0, 1]
        """
        diff = self._rho - other._rho
        eigenvalues = np.linalg.eigvalsh(diff)
        return float(0.5 * np.sum(np.abs(eigenvalues)))

    def bloch_vector(self, qubit: int) -> Tuple[float, float, float]:
        """
        Get Bloch vector for a single qubit (traces out others).

        Args:
            qubit: Qubit index

        Returns:
            (x, y, z) Bloch coordinates
        """
        reduced = self.partial_trace([qubit])
        return state_to_bloch(reduced._rho)

    def all_bloch_vectors(self) -> List[Tuple[float, float, float]]:
        """Get Bloch vectors for all qubits."""
        return [self.bloch_vector(q) for q in range(self._n_qubits)]

    def eigenvalues(self) -> np.ndarray:
        """Get eigenvalues of density matrix."""
        return np.linalg.eigvalsh(self._rho)

    def rank(self, tol: float = 1e-10) -> int:
        """Get rank of density matrix (number of non-zero eigenvalues)."""
        eigenvalues = np.linalg.eigvalsh(self._rho)
        return int(np.sum(eigenvalues > tol))

    def copy(self) -> 'DensityMatrix':
        """Create deep copy."""
        return DensityMatrix(self._n_qubits, self._rho.copy())

    def tensor(self, other: 'DensityMatrix') -> 'DensityMatrix':
        """
        Compute tensor product ρ ⊗ σ.

        Args:
            other: Another DensityMatrix

        Returns:
            Combined density matrix
        """
        new_rho = np.kron(self._rho, other._rho)
        return DensityMatrix(self._n_qubits + other._n_qubits, new_rho)

    def __str__(self) -> str:
        purity = self.purity()
        state_type = "pure" if self.is_pure() else "mixed"
        return f"DensityMatrix({self._n_qubits} qubits, {state_type}, purity={purity:.4f})"

    def __repr__(self) -> str:
        return f"DensityMatrix(n_qubits={self._n_qubits})"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'n_qubits': self._n_qubits,
            'rho_real': self._rho.real.tolist(),
            'rho_imag': self._rho.imag.tolist(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DensityMatrix':
        """Deserialize from dictionary."""
        rho = np.array(data['rho_real']) + 1j * np.array(data['rho_imag'])
        return cls(data['n_qubits'], rho)


# Export
__all__ = ['DensityMatrix', 'DensityMeasurementResult']
