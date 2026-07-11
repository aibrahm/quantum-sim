"""
Circuit Executor - Runs quantum circuits with state tracking.
Supports state vector and density matrix modes, noise, and step-by-step execution.
"""

import numpy as np
from typing import List, Dict, Optional, Union, Generator, Literal, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .circuit import QuantumCircuit, GateOperation, OperationType
from ..core.state_vector import StateVector
from ..core.density_matrix import DensityMatrix
from ..core.gates import get_gate, multi_qubit_gate, tensor_gate, H, S, Sdg
from ..core.channels import NoiseModel
from ..core.measurement import sample, projective_measure, measure_in_basis


class ExecutionMode(Enum):
    """Simulation mode."""
    STATEVECTOR = "statevector"
    DENSITY_MATRIX = "density_matrix"


@dataclass
class StateSnapshot:
    """Snapshot of circuit state at a particular step."""
    step: int
    operation_type: str
    operation_name: str
    qubits: List[int]
    params: List[float]
    probabilities: np.ndarray
    bloch_vectors: List[Tuple[float, float, float]]
    amplitudes: Optional[np.ndarray] = None  # For statevector mode
    density_matrix: Optional[np.ndarray] = None  # For density matrix mode
    measurement_outcome: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            'step': self.step,
            'operation_type': self.operation_type,
            'operation_name': self.operation_name,
            'qubits': self.qubits,
            'params': self.params,
            'probabilities': self.probabilities.tolist(),
            'bloch_vectors': self.bloch_vectors,
            'amplitudes_real': self.amplitudes.real.tolist() if self.amplitudes is not None else None,
            'amplitudes_imag': self.amplitudes.imag.tolist() if self.amplitudes is not None else None,
            'measurement_outcome': self.measurement_outcome,
        }


@dataclass
class ExecutionResult:
    """Result of circuit execution."""
    counts: Dict[str, int]
    shots: int
    final_state: Optional[Union[StateVector, DensityMatrix]] = None
    snapshots: List[StateSnapshot] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def get_probabilities(self) -> Dict[str, float]:
        """Convert counts to probabilities."""
        return {k: v / self.shots for k, v in self.counts.items()}

    def to_dict(self) -> dict:
        return {
            'counts': self.counts,
            'shots': self.shots,
            'probabilities': self.get_probabilities(),
            'snapshots': [s.to_dict() for s in self.snapshots],
            'execution_time_ms': self.execution_time_ms,
        }


class Executor:
    """
    Executes quantum circuits with configurable simulation mode and noise.
    """

    def __init__(
        self,
        circuit: QuantumCircuit,
        mode: Literal["statevector", "density_matrix"] = "statevector",
        noise_model: Optional[NoiseModel] = None,
        record_snapshots: bool = False
    ):
        """
        Initialize executor.

        Args:
            circuit: Circuit to execute
            mode: Simulation mode
            noise_model: Optional noise model
            record_snapshots: Whether to record state after each step
        """
        self._circuit = circuit
        self._mode = ExecutionMode(mode)
        self._noise_model = noise_model
        self._record_snapshots = record_snapshots

        # Initialize state
        if self._mode == ExecutionMode.STATEVECTOR and noise_model is None:
            self._state: Union[StateVector, DensityMatrix] = StateVector(circuit.n_qubits)
        else:
            # Use density matrix for noisy simulation
            self._state = DensityMatrix(circuit.n_qubits)
            if self._mode == ExecutionMode.STATEVECTOR and noise_model is not None:
                self._mode = ExecutionMode.DENSITY_MATRIX

        self._current_step = 0
        self._classical_bits = [0] * circuit.n_classical
        self._snapshots: List[StateSnapshot] = []

    @property
    def state(self) -> Union[StateVector, DensityMatrix]:
        """Current quantum state."""
        return self._state

    @property
    def mode(self) -> ExecutionMode:
        return self._mode

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def snapshots(self) -> List[StateSnapshot]:
        return self._snapshots.copy()

    def reset(self) -> None:
        """Reset executor to initial state."""
        if self._mode == ExecutionMode.STATEVECTOR:
            self._state = StateVector(self._circuit.n_qubits)
        else:
            self._state = DensityMatrix(self._circuit.n_qubits)
        self._current_step = 0
        self._classical_bits = [0] * self._circuit.n_classical
        self._snapshots = []

    def _create_snapshot(self, op_type: str, op_name: str,
                         qubits: List[int], params: List[float],
                         measurement_outcome: Optional[int] = None) -> StateSnapshot:
        """Create a state snapshot."""
        # Bloch vectors need a per-qubit partial trace (O(4^n)); only pay for it
        # when snapshots are actually being recorded for visualization.
        want_bloch = self._record_snapshots
        if isinstance(self._state, StateVector):
            probs = self._state.probabilities
            bloch = self._state.all_bloch_vectors() if want_bloch else []
            amps = self._state.amplitudes
            rho = None
        else:
            rho_matrix = self._state.rho
            probs = np.real(np.diag(rho_matrix))
            bloch = self._state.all_bloch_vectors() if want_bloch else []
            amps = None
            rho = rho_matrix

        return StateSnapshot(
            step=self._current_step,
            operation_type=op_type,
            operation_name=op_name,
            qubits=qubits,
            params=params,
            probabilities=probs,
            bloch_vectors=bloch,
            amplitudes=amps,
            density_matrix=rho,
            measurement_outcome=measurement_outcome
        )

    def step(self) -> Optional[StateSnapshot]:
        """
        Execute one step of the circuit.

        Returns:
            StateSnapshot if step executed, None if circuit complete
        """
        if self._current_step >= len(self._circuit.operations):
            return None

        op = self._circuit.operations[self._current_step]

        if op.op_type == OperationType.GATE:
            self._apply_gate(op.operation)
            snapshot = self._create_snapshot(
                'gate', op.operation.gate_name,
                op.operation.qubits, op.operation.params
            )

        elif op.op_type == OperationType.MEASUREMENT:
            outcome = self._apply_measurement(op.operation)
            snapshot = self._create_snapshot(
                'measurement', 'measure',
                op.operation.qubits, [],
                measurement_outcome=outcome
            )

        elif op.op_type == OperationType.RESET:
            self._apply_reset(op.qubits)
            snapshot = self._create_snapshot(
                'reset', 'reset', op.qubits, []
            )

        elif op.op_type == OperationType.BARRIER:
            snapshot = self._create_snapshot(
                'barrier', 'barrier', op.qubits, []
            )

        else:
            snapshot = None

        self._current_step += 1

        if self._record_snapshots and snapshot:
            self._snapshots.append(snapshot)

        return snapshot

    def _apply_gate(self, gate_op: GateOperation) -> None:
        """Apply a gate operation to the state."""
        gate_matrix = get_gate(gate_op.gate_name, gate_op.params if gate_op.params else None)

        self._state = self._state.apply_gate(gate_matrix, gate_op.qubits)

        # Apply noise if present
        if self._noise_model:
            self._apply_noise_after_gate(gate_op)

    def _apply_noise_after_gate(self, gate_op: GateOperation) -> None:
        """Apply noise after gate execution."""
        if not isinstance(self._state, DensityMatrix):
            # Convert to density matrix for noise
            self._state = DensityMatrix.from_state_vector(self._state.amplitudes)

        # Gate-specific noise
        kraus = self._noise_model.get_gate_noise(gate_op.gate_name)
        if kraus:
            for q in gate_op.qubits:
                self._state = self._state.apply_channel(kraus, [q])

        # Qubit-specific noise
        for q in gate_op.qubits:
            kraus = self._noise_model.get_qubit_noise(q)
            if kraus:
                self._state = self._state.apply_channel(kraus, [q])

        # Global noise
        if self._noise_model.global_noise:
            for q in gate_op.qubits:
                self._state = self._state.apply_channel(
                    self._noise_model.global_noise, [q]
                )

    def _rotate_basis(self, qubits: List[int], basis: str, undo: bool = False) -> None:
        """Rotate qubits between the given measurement basis and the Z basis.

        X basis: H maps X eigenstates to Z eigenstates (self-inverse).
        Y basis: Sdg then H maps Y eigenstates to Z eigenstates; H then S undoes it.
        """
        basis = basis.upper()
        if basis == 'Z':
            return
        if basis == 'X':
            gates = [H]
        elif basis == 'Y':
            gates = [H, S] if undo else [Sdg, H]
        else:
            raise ValueError(f"Unknown measurement basis: {basis}")

        for q in qubits:
            for gate in gates:
                self._state = self._state.apply_gate(gate, [q])

    def _apply_measurement(self, m_op) -> int:
        """Apply measurement and return outcome."""
        # Rotate to the Z basis, measure, then rotate the collapsed state back
        # so the post-measurement state is the eigenstate in the requested basis.
        self._rotate_basis(m_op.qubits, m_op.basis)

        result = self._state.measure(m_op.qubits)
        self._state = result.post_state
        outcome = result.outcome

        self._rotate_basis(m_op.qubits, m_op.basis, undo=True)

        # Apply readout error if noise model present
        if self._noise_model:
            outcome = self._noise_model.apply_readout_error(outcome, m_op.qubits)

        # Store in classical bits
        for i, cbit in enumerate(m_op.classical_bits):
            bit_val = (outcome >> i) & 1
            self._classical_bits[cbit] = bit_val

        return outcome

    def _apply_reset(self, qubits: List[int]) -> None:
        """Reset qubits to |0⟩."""
        for q in qubits:
            # Measure and conditionally flip
            if isinstance(self._state, StateVector):
                result = self._state.measure([q])
                self._state = result.post_state
                if result.outcome == 1:
                    from ..core.gates import X
                    self._state = self._state.apply_gate(X, [q])
            else:
                result = self._state.measure([q])
                self._state = result.post_state
                if result.outcome == 1:
                    from ..core.gates import X
                    self._state = self._state.apply_gate(X, [q])

    def run_all(self) -> None:
        """Execute all remaining steps."""
        while self.step() is not None:
            pass

    def run_to_step(self, target_step: int) -> None:
        """Run until reaching target step."""
        while self._current_step < target_step:
            if self.step() is None:
                break

    def _terminal_measurement_ops(self) -> Optional[List]:
        """Return the measurement ops if the circuit is unitary-then-measure.

        Eligible when every measurement sits after all gates and there are no
        resets (mid-circuit measurement/reset needs true per-shot handling).
        Returns None otherwise.
        """
        ops = self._circuit.operations
        measures = []
        seen_measure = False
        for op in ops:
            if op.op_type == OperationType.MEASUREMENT:
                seen_measure = True
                measures.append(op)
            elif op.op_type == OperationType.RESET:
                return None
            elif op.op_type == OperationType.GATE and seen_measure:
                # A gate after a measurement means feed-forward / mid-circuit logic.
                return None
        return measures if measures else None

    def _sample_terminal(self, measures: List, shots: int) -> Dict[str, int]:
        """Draw all shots at once from the final state's measurement distribution."""
        amps = self._state.amplitudes

        measured_qubits: List[int] = []
        measured_cbits: List[int] = []
        for op in measures:
            measured_qubits.extend(op.operation.qubits)
            measured_cbits.extend(op.operation.classical_bits)

        n_measured = len(measured_qubits)
        basis = np.arange(len(amps))
        outcome = np.zeros(len(amps), dtype=np.int64)
        for k, q in enumerate(measured_qubits):
            outcome |= ((basis >> q) & 1) << k

        probs = np.zeros(2 ** n_measured)
        np.add.at(probs, outcome, np.abs(amps) ** 2)
        probs = np.maximum(probs, 0)
        probs /= probs.sum()

        draws = np.random.choice(2 ** n_measured, size=shots, p=probs)
        values, freqs = np.unique(draws, return_counts=True)

        counts: Dict[str, int] = {}
        for value, freq in zip(values, freqs):
            cbits = [0] * self._circuit.n_classical
            for k, cbit in enumerate(measured_cbits):
                cbits[cbit] = int((value >> k) & 1)
            key = ''.join(str(b) for b in reversed(cbits))
            counts[key] = counts.get(key, 0) + int(freq)

        return counts

    def run(self, shots: int = 1024) -> ExecutionResult:
        """
        Execute circuit and sample measurements.

        Args:
            shots: Number of measurement shots

        Returns:
            ExecutionResult with counts and optional state snapshots
        """
        import time
        start_time = time.time()

        # Check if circuit has measurements
        has_measurement = any(
            op.op_type == OperationType.MEASUREMENT
            for op in self._circuit.operations
        )

        terminal_measures = self._terminal_measurement_ops()
        if (terminal_measures is not None
                and self._mode == ExecutionMode.STATEVECTOR
                and self._noise_model is None):
            # Fast path: simulate the unitary part once, then draw every shot from
            # the final distribution instead of re-running the circuit per shot.
            state = StateVector(self._circuit.n_qubits)
            for op in self._circuit.operations:
                if op.op_type == OperationType.GATE:
                    gate_matrix = get_gate(
                        op.operation.gate_name,
                        op.operation.params if op.operation.params else None
                    )
                    state = state.apply_gate(gate_matrix, op.operation.qubits)
                elif op.op_type == OperationType.BARRIER:
                    continue
                else:
                    break
            self._state = state
            # Rotate measured qubits into the Z frame of their requested basis
            # so the sampled distribution reflects X/Y basis measurements.
            for op in terminal_measures:
                self._rotate_basis(op.operation.qubits, op.operation.basis)
            counts = self._sample_terminal(terminal_measures, shots)
            end_time = time.time()
            return ExecutionResult(
                counts=counts,
                shots=shots,
                final_state=None,
                snapshots=[],
                execution_time_ms=(end_time - start_time) * 1000
            )

        if has_measurement:
            # Run multiple shots with measurements
            counts: Dict[str, int] = {}

            for _ in range(shots):
                self.reset()
                self.run_all()

                # Read classical bits as outcome
                outcome_bits = ''.join(str(b) for b in reversed(self._classical_bits))
                counts[outcome_bits] = counts.get(outcome_bits, 0) + 1

            final_state = None  # State is collapsed after measurement

        else:
            # No measurements - sample from final state
            self.reset()
            self.run_all()

            if isinstance(self._state, StateVector):
                counts = self._state.sample(shots)
            else:
                counts = self._state.sample(shots)

            final_state = self._state.copy()

        end_time = time.time()

        return ExecutionResult(
            counts=counts,
            shots=shots,
            final_state=final_state,
            snapshots=self._snapshots if self._record_snapshots else [],
            execution_time_ms=(end_time - start_time) * 1000
        )

    def run_statevector(self) -> Union[StateVector, DensityMatrix]:
        """
        Run circuit and return final state (no sampling).

        Returns:
            Final state vector or density matrix
        """
        self.reset()
        self.run_all()
        return self._state.copy()

    def step_generator(self) -> Generator[StateSnapshot, None, None]:
        """
        Generator for step-by-step execution.

        Yields:
            StateSnapshot after each step
        """
        self.reset()
        self._record_snapshots = True

        while True:
            snapshot = self.step()
            if snapshot is None:
                break
            yield snapshot

    def get_state_at_step(self, target_step: int) -> StateSnapshot:
        """
        Get state snapshot at specific step.

        Args:
            target_step: Step number (0-indexed)

        Returns:
            StateSnapshot at that step
        """
        self.reset()
        self._record_snapshots = True

        for _ in range(target_step + 1):
            snapshot = self.step()
            if snapshot is None:
                break

        if self._snapshots and target_step < len(self._snapshots):
            return self._snapshots[target_step]

        return self._create_snapshot('final', 'end', [], [])


def run_circuit(
    circuit: QuantumCircuit,
    shots: int = 1024,
    mode: str = "statevector",
    noise_model: Optional[NoiseModel] = None,
    record_snapshots: bool = False
) -> ExecutionResult:
    """
    Convenience function to run a circuit.

    Args:
        circuit: Circuit to run
        shots: Number of measurement shots
        mode: Simulation mode
        noise_model: Optional noise model
        record_snapshots: Record state after each step

    Returns:
        ExecutionResult
    """
    executor = Executor(circuit, mode, noise_model, record_snapshots)
    return executor.run(shots)


def get_statevector(circuit: QuantumCircuit) -> StateVector:
    """
    Get final state vector of circuit (no measurements executed).

    Args:
        circuit: Circuit to simulate

    Returns:
        Final StateVector
    """
    executor = Executor(circuit, "statevector", None, False)
    state = executor.run_statevector()
    if isinstance(state, DensityMatrix):
        raise ValueError("Circuit contains operations requiring density matrix")
    return state


def get_density_matrix(
    circuit: QuantumCircuit,
    noise_model: Optional[NoiseModel] = None
) -> DensityMatrix:
    """
    Get final density matrix of circuit.

    Args:
        circuit: Circuit to simulate
        noise_model: Optional noise model

    Returns:
        Final DensityMatrix
    """
    executor = Executor(circuit, "density_matrix", noise_model, False)
    state = executor.run_statevector()
    if isinstance(state, StateVector):
        return DensityMatrix.from_state_vector(state.amplitudes)
    return state


# Export
__all__ = [
    'Executor',
    'ExecutionMode',
    'StateSnapshot',
    'ExecutionResult',
    'run_circuit',
    'get_statevector',
    'get_density_matrix',
]
