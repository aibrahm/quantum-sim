"""
Circuit optimization passes for quantum circuits.
Implements gate cancellation, single-qubit fusion, commutation, CX optimization, and rotation merging.
"""

import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..circuit.circuit import (
    QuantumCircuit, CircuitOperation, GateOperation,
    OperationType
)
from ..core.gates import get_gate


def _rebuild(original: QuantumCircuit, ops: List[CircuitOperation]) -> QuantumCircuit:
    """Build a new circuit from an operations list, preserving qubit/classical counts."""
    qc = QuantumCircuit(original.n_qubits, original.n_classical, original.name)
    for op in ops:
        qc._operations.append(op)
    return qc


@dataclass
class OptimizationResult:
    """Result of circuit optimization."""
    original_circuit: QuantumCircuit
    optimized_circuit: QuantumCircuit
    original_depth: int
    optimized_depth: int
    original_gate_count: int
    optimized_gate_count: int
    original_cx_count: int
    optimized_cx_count: int
    passes_applied: List[str]
    reduction_percentage: float


class OptimizationPass(ABC):
    """Base class for optimization passes."""

    name: str = ""

    @abstractmethod
    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """Apply optimization pass to a circuit."""
        ...


SELF_INVERSE_GATES = {'X', 'Y', 'Z', 'H', 'CX', 'CNOT', 'CY', 'CZ', 'SWAP'}

INVERSE_PAIRS = {
    ('S', 'Sdg'), ('Sdg', 'S'),
    ('T', 'Tdg'), ('Tdg', 'T'),
    ('SX', 'SXdg'), ('SXdg', 'SX'),
}


class GateCancellation(OptimizationPass):
    """Remove adjacent inverse gate pairs."""

    name = "gate_cancellation"

    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        ops = list(circuit.operations)
        changed = True

        while changed:
            changed = False
            new_ops = []
            skip_next = False

            for i in range(len(ops)):
                if skip_next:
                    skip_next = False
                    continue

                if i + 1 < len(ops):
                    op1 = ops[i]
                    op2 = ops[i + 1]

                    if self._gates_cancel(op1, op2):
                        skip_next = True
                        changed = True
                        continue

                new_ops.append(ops[i])

            ops = new_ops

        return _rebuild(circuit, ops)

    def _gates_cancel(self, op1: CircuitOperation, op2: CircuitOperation) -> bool:
        """Check if two adjacent operations cancel."""
        if op1.op_type != OperationType.GATE or op2.op_type != OperationType.GATE:
            return False

        g1 = op1.operation
        g2 = op2.operation

        if g1.qubits != g2.qubits:
            return False

        if g1.gate_name == g2.gate_name and g1.gate_name in SELF_INVERSE_GATES:
            if not g1.params and not g2.params:
                return True

        if (g1.gate_name, g2.gate_name) in INVERSE_PAIRS:
            return True

        if g1.gate_name == g2.gate_name and g1.gate_name in ('Rx', 'Ry', 'Rz', 'Phase'):
            if len(g1.params) == 1 and len(g2.params) == 1:
                if abs(g1.params[0] + g2.params[0]) < 1e-10:
                    return True

        return False


class SingleQubitFusion(OptimizationPass):
    """Merge consecutive single-qubit gates into one U3."""

    SINGLE_QUBIT_GATES = {
        'I', 'X', 'Y', 'Z', 'H', 'S', 'Sdg', 'T', 'Tdg',
        'SX', 'SXdg', 'Rx', 'Ry', 'Rz', 'Phase', 'U1', 'U2', 'U3'
    }

    name = "single_qubit_fusion"

    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        ops = list(circuit.operations)
        result_ops = []
        i = 0

        while i < len(ops):
            op = ops[i]

            if (op.op_type == OperationType.GATE and
                    op.operation.gate_name in self.SINGLE_QUBIT_GATES and
                    len(op.operation.qubits) == 1):

                qubit = op.operation.qubits[0]
                chain = [op]
                j = i + 1

                while j < len(ops):
                    next_op = ops[j]
                    if (next_op.op_type == OperationType.GATE and
                            next_op.operation.gate_name in self.SINGLE_QUBIT_GATES and
                            len(next_op.operation.qubits) == 1 and
                            next_op.operation.qubits[0] == qubit):
                        chain.append(next_op)
                        j += 1
                    else:
                        break

                if len(chain) > 1:
                    fused = self._fuse_chain(chain, qubit)
                    if fused is not None:
                        result_ops.append(fused)
                    i = j
                    continue

            result_ops.append(op)
            i += 1

        return _rebuild(circuit, result_ops)

    def _fuse_chain(self, chain: List[CircuitOperation], qubit: int) -> Optional[CircuitOperation]:
        """Fuse a chain of single-qubit gates into one U3."""
        combined = np.eye(2, dtype=complex)
        for op in chain:
            gate = op.operation
            params = gate.params if gate.params else None
            mat = get_gate(gate.gate_name, params)
            combined = mat @ combined

        if np.allclose(combined, np.eye(2, dtype=complex), atol=1e-10):
            return None

        theta, phi, lam = self._zyz_decomposition(combined)

        gate_op = GateOperation(
            gate_name='U3',
            qubits=[qubit],
            params=[theta, phi, lam],
            label=f'fused({len(chain)})'
        )
        return CircuitOperation(
            op_type=OperationType.GATE,
            operation=gate_op,
            qubits=[qubit]
        )

    def _zyz_decomposition(self, U: np.ndarray) -> Tuple[float, float, float]:
        """Decompose a 2x2 unitary into ZYZ Euler angles."""
        det = np.linalg.det(U)
        phase = np.angle(det) / 2
        U_su2 = U * np.exp(-1j * phase)

        theta = 2 * np.arccos(np.clip(np.abs(U_su2[0, 0]), 0, 1))

        if np.abs(np.sin(theta / 2)) < 1e-10:
            phi = 0.0
            lam = float(np.angle(U_su2[1, 1]))
        elif np.abs(np.cos(theta / 2)) < 1e-10:
            phi = float(np.angle(U_su2[1, 0]))
            lam = float(-np.angle(U_su2[0, 1]))
        else:
            phi = float(np.angle(U_su2[1, 0]))
            lam = float(-np.angle(U_su2[0, 1]))

        return float(theta), phi, lam


COMMUTING_PAIRS = {
    frozenset({'Z', 'S', 'Sdg', 'T', 'Tdg', 'Rz', 'Phase', 'CZ'}),
}


class CommutationAnalysis(OptimizationPass):
    """Reorder commuting gates to enable further cancellations."""

    DIAGONAL_GATES = {'Z', 'S', 'Sdg', 'T', 'Tdg', 'Rz', 'Phase', 'U1', 'CZ'}

    name = "commutation_analysis"

    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        ops = list(circuit.operations)
        changed = True
        max_iterations = 10

        for _ in range(max_iterations):
            if not changed:
                break
            changed = False

            for i in range(len(ops) - 1):
                if self._should_swap(ops[i], ops[i + 1]):
                    ops[i], ops[i + 1] = ops[i + 1], ops[i]
                    changed = True

        return _rebuild(circuit, ops)

    def _should_swap(self, op1: CircuitOperation, op2: CircuitOperation) -> bool:
        """Determine if swapping two operations is beneficial."""
        if op1.op_type != OperationType.GATE or op2.op_type != OperationType.GATE:
            return False

        g1, g2 = op1.operation, op2.operation

        if not self._gates_commute(g1, g2):
            return False

        if g1.gate_name == g2.gate_name and g1.qubits == g2.qubits:
            return False

        return g1.gate_name > g2.gate_name

    def _gates_commute(self, g1: GateOperation, g2: GateOperation) -> bool:
        """Check if two gates commute."""
        if not set(g1.qubits) & set(g2.qubits):
            return True

        if g1.gate_name in self.DIAGONAL_GATES and g2.gate_name in self.DIAGONAL_GATES:
            return True

        if g1.gate_name == g2.gate_name and g1.qubits == g2.qubits:
            return True

        if g1.gate_name == 'Z' and g2.gate_name in ('CX', 'CNOT'):
            if g1.qubits[0] == g2.qubits[1]:
                return True
        if g2.gate_name == 'Z' and g1.gate_name in ('CX', 'CNOT'):
            if g2.qubits[0] == g1.qubits[1]:
                return True

        if g1.gate_name == 'X' and g2.gate_name in ('CX', 'CNOT'):
            if g1.qubits[0] == g2.qubits[0]:
                return True
        if g2.gate_name == 'X' and g1.gate_name in ('CX', 'CNOT'):
            if g2.qubits[0] == g1.qubits[0]:
                return True

        return False


class CXOptimization(OptimizationPass):
    """Reduce CNOT gate count using circuit identities."""

    name = "cx_optimization"

    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        ops = list(circuit.operations)
        changed = True

        while changed:
            changed = False

            new_ops = []
            skip_next = False
            for i in range(len(ops)):
                if skip_next:
                    skip_next = False
                    continue

                if i + 1 < len(ops):
                    if self._cnots_cancel(ops[i], ops[i + 1]):
                        skip_next = True
                        changed = True
                        continue

                new_ops.append(ops[i])
            ops = new_ops

            new_ops = []
            i = 0
            while i < len(ops):
                if i + 2 < len(ops) and self._is_swap_pattern(ops[i], ops[i + 1], ops[i + 2]):
                    qubit_a = ops[i].operation.qubits[0]
                    qubit_b = ops[i].operation.qubits[1]
                    swap_op = GateOperation(gate_name='SWAP', qubits=[qubit_a, qubit_b])
                    new_ops.append(CircuitOperation(
                        op_type=OperationType.GATE,
                        operation=swap_op,
                        qubits=[qubit_a, qubit_b]
                    ))
                    i += 3
                    changed = True
                else:
                    new_ops.append(ops[i])
                    i += 1
            ops = new_ops

        return _rebuild(circuit, ops)

    def _cnots_cancel(self, op1: CircuitOperation, op2: CircuitOperation) -> bool:
        """Check if two CNOTs cancel."""
        if op1.op_type != OperationType.GATE or op2.op_type != OperationType.GATE:
            return False
        g1, g2 = op1.operation, op2.operation
        if g1.gate_name in ('CX', 'CNOT') and g2.gate_name in ('CX', 'CNOT'):
            return g1.qubits == g2.qubits
        return False

    def _is_swap_pattern(self, op1: CircuitOperation, op2: CircuitOperation, op3: CircuitOperation) -> bool:
        """Check for CNOT(a,b) CNOT(b,a) CNOT(a,b) = SWAP pattern."""
        if not all(op.op_type == OperationType.GATE for op in [op1, op2, op3]):
            return False

        g1, g2, g3 = op1.operation, op2.operation, op3.operation
        if not all(g.gate_name in ('CX', 'CNOT') for g in [g1, g2, g3]):
            return False

        if (g1.qubits == g3.qubits and
                g2.qubits == [g1.qubits[1], g1.qubits[0]]):
            return True

        return False


class RotationMerging(OptimizationPass):
    """Merge adjacent rotation gates on the same axis."""

    ROTATION_GATES = {'Rx', 'Ry', 'Rz', 'Phase', 'U1'}

    name = "rotation_merging"

    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        ops = list(circuit.operations)
        changed = True

        while changed:
            changed = False
            new_ops = []
            skip_next = False

            for i in range(len(ops)):
                if skip_next:
                    skip_next = False
                    continue

                if i + 1 < len(ops):
                    merged = self._try_merge(ops[i], ops[i + 1])
                    if merged is not None:
                        new_ops.append(merged)
                        skip_next = True
                        changed = True
                        continue

                new_ops.append(ops[i])

            ops = new_ops

        return _rebuild(circuit, ops)

    def _try_merge(self, op1: CircuitOperation, op2: CircuitOperation) -> Optional[CircuitOperation]:
        """Try to merge two rotation gates."""
        if op1.op_type != OperationType.GATE or op2.op_type != OperationType.GATE:
            return None

        g1, g2 = op1.operation, op2.operation

        if (g1.gate_name not in self.ROTATION_GATES or
                g2.gate_name not in self.ROTATION_GATES):
            return None

        if g1.gate_name != g2.gate_name or g1.qubits != g2.qubits:
            return None

        if len(g1.params) != 1 or len(g2.params) != 1:
            return None

        merged_angle = g1.params[0] + g2.params[0]

        if abs(merged_angle % (2 * np.pi)) < 1e-10:
            return None

        gate_op = GateOperation(
            gate_name=g1.gate_name,
            qubits=g1.qubits[:],
            params=[merged_angle]
        )
        return CircuitOperation(
            op_type=OperationType.GATE,
            operation=gate_op,
            qubits=g1.qubits[:]
        )


DEFAULT_PASSES = [
    CommutationAnalysis,
    GateCancellation,
    RotationMerging,
    SingleQubitFusion,
    CXOptimization,
]


def optimize_circuit(
    circuit: QuantumCircuit,
    passes: Optional[List[type]] = None,
    iterations: int = 3
) -> OptimizationResult:
    """Run optimization passes on a circuit. Returns OptimizationResult."""
    from ..analysis.circuit_stats import circuit_depth, gate_count, two_qubit_gate_count

    if passes is None:
        passes = DEFAULT_PASSES

    pass_instances = [p() for p in passes]
    passes_applied = []

    orig_depth = circuit_depth(circuit)
    orig_gates = gate_count(circuit)
    orig_total = sum(orig_gates.values())
    orig_cx = two_qubit_gate_count(circuit)

    current = circuit
    for iteration in range(iterations):
        for opt_pass in pass_instances:
            optimized = opt_pass.run(current)
            if len(optimized) != len(current):
                passes_applied.append(f"{opt_pass.name} (iter {iteration + 1})")
            current = optimized

    opt_depth = circuit_depth(current)
    opt_gates = gate_count(current)
    opt_total = sum(opt_gates.values())
    opt_cx = two_qubit_gate_count(current)

    reduction = (1 - opt_total / max(orig_total, 1)) * 100

    return OptimizationResult(
        original_circuit=circuit,
        optimized_circuit=current,
        original_depth=orig_depth,
        optimized_depth=opt_depth,
        original_gate_count=orig_total,
        optimized_gate_count=opt_total,
        original_cx_count=orig_cx,
        optimized_cx_count=opt_cx,
        passes_applied=passes_applied,
        reduction_percentage=reduction,
    )
