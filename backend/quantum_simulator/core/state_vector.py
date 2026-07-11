"""Pure quantum state representation."""

import numpy as np
from typing import List, Tuple, Optional, Union, Dict
from dataclasses import dataclass

from .gates import GateMatrix, multi_qubit_gate, apply_gate_to_statevector
from .utils import (
    tensor_product, partial_trace_simple, state_to_bloch,
    normalize_state, outer_product
)


@dataclass
class MeasurementResult:
    """Result of a quantum measurement."""
    outcome: int  # Measured value (integer representation)
    outcome_bits: str  # Binary string representation
    probability: float  # Probability of this outcome
    post_state: Optional['StateVector'] = None  # Post-measurement state


class StateVector:
    """
    Pure quantum state represented as a complex amplitude vector.

    The state |ψ⟩ = Σᵢ αᵢ|i⟩ where |i⟩ are computational basis states
    and αᵢ are complex amplitudes satisfying Σᵢ|αᵢ|² = 1.

    Qubit ordering: |q_{n-1} q_{n-2} ... q_1 q_0⟩
    Index i corresponds to binary representation of i.
    """

    MAX_QUBITS = 20  # Maximum supported qubits (2^20 = ~1M amplitudes)

    def __init__(self, n_qubits: int, initial_state: Optional[np.ndarray] = None):
        if n_qubits < 1:
            raise ValueError("Number of qubits must be at least 1")
        if n_qubits > self.MAX_QUBITS:
            raise ValueError(f"Maximum {self.MAX_QUBITS} qubits supported")

        self._n_qubits = n_qubits
        self._dim = 2 ** n_qubits

        if initial_state is not None:
            if initial_state.shape != (self._dim,):
                raise ValueError(f"Initial state must have shape ({self._dim},)")
            self._amplitudes = normalize_state(initial_state.astype(complex))
        else:
            # Initialize to |0...0⟩
            self._amplitudes = np.zeros(self._dim, dtype=complex)
            self._amplitudes[0] = 1.0

    @classmethod
    def from_label(cls, label: str) -> 'StateVector':
        """Create a computational basis state from a binary string like '010'."""
        # Remove ket notation if present
        label = label.replace('|', '').replace('⟩', '').replace('>', '')

        n_qubits = len(label)
        index = int(label, 2)

        state = np.zeros(2 ** n_qubits, dtype=complex)
        state[index] = 1.0

        return cls(n_qubits, state)

    @classmethod
    def from_amplitudes(cls, amplitudes: Union[List[complex], np.ndarray]) -> 'StateVector':
        """Create a state vector from explicit amplitudes (normalized)."""
        amplitudes = np.asarray(amplitudes, dtype=complex)
        dim = len(amplitudes)
        n_qubits = int(np.log2(dim))

        if 2 ** n_qubits != dim:
            raise ValueError(f"Amplitude count {dim} is not a power of 2")

        return cls(n_qubits, amplitudes)

    @classmethod
    def bell_state(cls, state_type: str = 'phi+') -> 'StateVector':
        """Create a Bell state ('phi+', 'phi-', 'psi+', or 'psi-')."""
        if state_type == 'phi+':
            # |Φ+⟩ = (|00⟩ + |11⟩)/√2
            amps = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
        elif state_type == 'phi-':
            # |Φ-⟩ = (|00⟩ - |11⟩)/√2
            amps = np.array([1, 0, 0, -1], dtype=complex) / np.sqrt(2)
        elif state_type == 'psi+':
            # |Ψ+⟩ = (|01⟩ + |10⟩)/√2
            amps = np.array([0, 1, 1, 0], dtype=complex) / np.sqrt(2)
        elif state_type == 'psi-':
            # |Ψ-⟩ = (|01⟩ - |10⟩)/√2
            amps = np.array([0, 1, -1, 0], dtype=complex) / np.sqrt(2)
        else:
            raise ValueError(f"Unknown Bell state type: {state_type}")

        return cls(2, amps)

    @classmethod
    def ghz_state(cls, n_qubits: int) -> 'StateVector':
        """Create a GHZ state: (|00...0> + |11...1>)/sqrt(2)."""
        dim = 2 ** n_qubits
        amps = np.zeros(dim, dtype=complex)
        amps[0] = 1 / np.sqrt(2)  # |00...0⟩
        amps[-1] = 1 / np.sqrt(2)  # |11...1⟩
        return cls(n_qubits, amps)

    @classmethod
    def w_state(cls, n_qubits: int) -> 'StateVector':
        """Create a W state with one excitation equally spread across qubits."""
        dim = 2 ** n_qubits
        amps = np.zeros(dim, dtype=complex)

        # W state has one excitation in each position
        norm = 1 / np.sqrt(n_qubits)
        for i in range(n_qubits):
            idx = 1 << i  # 2^i
            amps[idx] = norm

        return cls(n_qubits, amps)

    @property
    def n_qubits(self) -> int:
        """Number of qubits in the system."""
        return self._n_qubits

    @property
    def dim(self) -> int:
        """Dimension of the Hilbert space (2^n)."""
        return self._dim

    @property
    def amplitudes(self) -> np.ndarray:
        """Complex amplitude vector (read-only copy)."""
        return self._amplitudes.copy()

    @property
    def probabilities(self) -> np.ndarray:
        """Probability distribution |αᵢ|² for each basis state."""
        return np.abs(self._amplitudes) ** 2

    def apply_gate(self, gate: GateMatrix, qubits: List[int]) -> 'StateVector':
        """Apply a quantum gate to specified qubits, returning a new state."""
        # Validate qubits
        for q in qubits:
            if q < 0 or q >= self._n_qubits:
                raise ValueError(f"Qubit index {q} out of range [0, {self._n_qubits})")

        new_amplitudes = apply_gate_to_statevector(
            self._amplitudes, gate, qubits, self._n_qubits
        )

        return StateVector(self._n_qubits, new_amplitudes)

    def apply_gate_inplace(self, gate: GateMatrix, qubits: List[int]) -> None:
        """Apply a quantum gate in place."""
        for q in qubits:
            if q < 0 or q >= self._n_qubits:
                raise ValueError(f"Qubit index {q} out of range")

        self._amplitudes = apply_gate_to_statevector(
            self._amplitudes, gate, qubits, self._n_qubits
        )

    def measure(self, qubits: Optional[List[int]] = None,
                collapse: bool = True) -> MeasurementResult:
        """Projective measurement on specified qubits (None = all)."""
        if qubits is None:
            qubits = list(range(self._n_qubits))

        # Validate qubits
        for q in qubits:
            if q < 0 or q >= self._n_qubits:
                raise ValueError(f"Qubit index {q} out of range")

        n_measured = len(qubits)

        # Calculate probabilities for each measurement outcome
        outcome_probs = np.zeros(2 ** n_measured)

        for i in range(self._dim):
            # Extract bits for measured qubits
            outcome_idx = 0
            for k, q in enumerate(qubits):
                bit = (i >> q) & 1
                outcome_idx |= bit << k
            outcome_probs[outcome_idx] += np.abs(self._amplitudes[i]) ** 2

        # Sample outcome
        outcome = np.random.choice(2 ** n_measured, p=outcome_probs)
        outcome_bits = format(outcome, f'0{n_measured}b')

        if not collapse:
            return MeasurementResult(
                outcome=outcome,
                outcome_bits=outcome_bits,
                probability=outcome_probs[outcome]
            )

        # Collapse state
        new_amplitudes = np.zeros(self._dim, dtype=complex)

        for i in range(self._dim):
            # Check if this basis state matches the measurement outcome
            match = True
            for k, q in enumerate(qubits):
                bit = (i >> q) & 1
                expected = (outcome >> k) & 1
                if bit != expected:
                    match = False
                    break

            if match:
                new_amplitudes[i] = self._amplitudes[i]

        # Normalize
        norm = np.linalg.norm(new_amplitudes)
        if norm > 1e-15:
            new_amplitudes /= norm

        post_state = StateVector(self._n_qubits, new_amplitudes)

        return MeasurementResult(
            outcome=outcome,
            outcome_bits=outcome_bits,
            probability=outcome_probs[outcome],
            post_state=post_state
        )

    def sample(self, shots: int = 1024, qubits: Optional[List[int]] = None) -> Dict[str, int]:
        """Sample measurement outcomes without state collapse."""
        if qubits is None:
            qubits = list(range(self._n_qubits))

        n_measured = len(qubits)

        # Calculate outcome probabilities
        outcome_probs = np.zeros(2 ** n_measured)

        for i in range(self._dim):
            outcome_idx = 0
            for k, q in enumerate(qubits):
                bit = (i >> q) & 1
                outcome_idx |= bit << k
            outcome_probs[outcome_idx] += np.abs(self._amplitudes[i]) ** 2

        # Sample
        outcomes = np.random.choice(2 ** n_measured, size=shots, p=outcome_probs)

        # Count
        counts: Dict[str, int] = {}
        for outcome in outcomes:
            key = format(outcome, f'0{n_measured}b')
            counts[key] = counts.get(key, 0) + 1

        return counts

    def expectation(self, observable: np.ndarray,
                    qubits: Optional[List[int]] = None) -> float:
        """Expectation value <psi|O|psi>."""
        if qubits is None:
            op = observable
        else:
            op = multi_qubit_gate(observable, qubits, self._n_qubits)

        result = np.vdot(self._amplitudes, op @ self._amplitudes)
        return float(np.real(result))

    def variance(self, observable: np.ndarray,
                 qubits: Optional[List[int]] = None) -> float:
        """Variance <O^2> - <O>^2."""
        exp_O = self.expectation(observable, qubits)
        exp_O2 = self.expectation(observable @ observable, qubits)
        return exp_O2 - exp_O ** 2

    def to_density_matrix(self) -> np.ndarray:
        """Convert to density matrix |psi><psi|."""
        return outer_product(self._amplitudes, self._amplitudes)

    def reduced_density_matrix(self, keep_qubits: List[int]) -> np.ndarray:
        """Reduced density matrix, tracing out qubits not in keep_qubits."""
        rho = self.to_density_matrix()
        trace_out = [q for q in range(self._n_qubits) if q not in keep_qubits]
        return partial_trace_simple(rho, trace_out, self._n_qubits)

    def bloch_vector(self, qubit: int) -> Tuple[float, float, float]:
        """Bloch sphere (x, y, z) for a single qubit, tracing out others."""
        if self._n_qubits == 1:
            return state_to_bloch(self._amplitudes)

        # Get reduced density matrix for this qubit
        rho_q = self.reduced_density_matrix([qubit])
        return state_to_bloch(rho_q)

    def all_bloch_vectors(self) -> List[Tuple[float, float, float]]:
        """Bloch vectors for all qubits."""
        return [self.bloch_vector(q) for q in range(self._n_qubits)]

    def purity(self) -> float:
        """Purity Tr(rho^2). Always 1.0 for pure states."""
        return 1.0  # Pure states always have purity 1

    def entropy(self, base: float = 2) -> float:
        """Von Neumann entropy. Always 0.0 for pure states."""
        return 0.0  # Pure states have zero entropy

    def fidelity(self, other: 'StateVector') -> float:
        """Fidelity |<psi|phi>|^2."""
        if self._n_qubits != other._n_qubits:
            raise ValueError("States must have same number of qubits")
        overlap = np.vdot(self._amplitudes, other._amplitudes)
        return float(np.abs(overlap) ** 2)

    def inner_product(self, other: 'StateVector') -> complex:
        """Inner product <self|other>."""
        return complex(np.vdot(self._amplitudes, other._amplitudes))

    def copy(self) -> 'StateVector':
        """Create a deep copy of this state."""
        return StateVector(self._n_qubits, self._amplitudes.copy())

    def tensor(self, other: 'StateVector') -> 'StateVector':
        """Tensor product |self> x |other>."""
        new_amplitudes = tensor_product(self._amplitudes, other._amplitudes)
        return StateVector(self._n_qubits + other._n_qubits, new_amplitudes)

    def __str__(self) -> str:
        """String representation showing non-zero amplitudes."""
        terms = []
        for i in range(min(self._dim, 16)):  # Show up to 16 terms
            amp = self._amplitudes[i]
            if np.abs(amp) > 1e-10:
                label = format(i, f'0{self._n_qubits}b')
                if np.abs(amp.imag) < 1e-10:
                    terms.append(f"({amp.real:.4f})|{label}⟩")
                else:
                    terms.append(f"({amp:.4f})|{label}⟩")

        if self._dim > 16:
            terms.append("...")

        return " + ".join(terms) if terms else "|0⟩"

    def __repr__(self) -> str:
        return f"StateVector(n_qubits={self._n_qubits})"

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            'n_qubits': self._n_qubits,
            'amplitudes_real': self._amplitudes.real.tolist(),
            'amplitudes_imag': self._amplitudes.imag.tolist(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StateVector':
        """Deserialize from dictionary."""
        amps = np.array(data['amplitudes_real']) + 1j * np.array(data['amplitudes_imag'])
        return cls(data['n_qubits'], amps)
