"""
Circuit Optimization — Multi-pass compiler-style optimization for quantum circuits.

Implements standard quantum circuit optimization techniques:
1. Gate Cancellation: Remove adjacent inverse gate pairs (XX=I, HH=I, etc.)
2. Single-Qubit Fusion: Merge consecutive single-qubit gates into one U3 gate
3. Commutation Analysis: Reorder gates to enable further cancellations
4. CX Optimization: Reduce CNOT count using known identities

These passes are analogous to classical compiler optimizations (dead code
elimination, instruction combining, instruction scheduling) applied to
quantum circuits.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from copy import deepcopy

from ..circuit.circuit import (
    QuantumCircuit, CircuitOperation, GateOperation,
    OperationType
)
from ..core.gates import get_gate, is_unitary, GateMatrix


# =============================================================================
# Optimization Infrastructure
# =============================================================================

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

    def summary(self) -> Dict:
        return {
            'original_depth': self.original_depth,
            'optimized_depth': self.optimized_depth,
            'depth_reduction': f'{(1 - self.optimized_depth / max(self.original_depth, 1)) * 100:.1f}%',
            'original_gates': self.original_gate_count,
            'optimized_gates': self.optimized_gate_count,
            'gate_reduction': f'{self.reduction_percentage:.1f}%',
            'original_cx': self.original_cx_count,
            'optimized_cx': self.optimized_cx_count,
            'passes': self.passes_applied,
        }


class OptimizationPass(ABC):
    """Base class for optimization passes."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this optimization pass."""
        ...

    @abstractmethod
    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Apply optimization pass to a circuit.

        Args:
            circuit: Input circuit

        Returns:
            Optimized circuit (may be the same object if no changes)
        """
        ...


# =============================================================================
# Gate Cancellation Pass
# =============================================================================

# Gates that are self-inverse: G · G = I
SELF_INVERSE_GATES = {'X', 'Y', 'Z', 'H', 'CX', 'CNOT', 'CY', 'CZ', 'SWAP'}

# Inverse pairs: G₁ · G₂ = I
INVERSE_PAIRS = {
    ('S', 'Sdg'), ('Sdg', 'S'),
    ('T', 'Tdg'), ('Tdg', 'T'),
    ('SX', 'SXdg'), ('SXdg', 'SX'),
}


class GateCancellation(OptimizationPass):
    """
    Remove adjacent pairs of gates that cancel to identity.

    Detects:
    - Self-inverse gates: XX = I, HH = I, CNOT·CNOT = I
    - Inverse pairs: S·S† = I, T·T† = I
    - Rotation cancellation: Rx(θ)·Rx(-θ) = I

    This is analogous to algebraic simplification in classical compilers.
    """

    @property
    def name(self) -> str:
        return "gate_cancellation"

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

        return self._rebuild_circuit(circuit, ops)

    def _gates_cancel(self, op1: CircuitOperation, op2: CircuitOperation) -> bool:
        """Check if two adjacent operations cancel."""
        if op1.op_type != OperationType.GATE or op2.op_type != OperationType.GATE:
            return False

        g1 = op1.operation
        g2 = op2.operation

        # Must act on same qubits
        if g1.qubits != g2.qubits:
            return False

        # Self-inverse check
        if g1.gate_name == g2.gate_name and g1.gate_name in SELF_INVERSE_GATES:
            if not g1.params and not g2.params:
                return True

        # Inverse pair check
        if (g1.gate_name, g2.gate_name) in INVERSE_PAIRS:
            return True

        # Rotation cancellation: Rx(θ)Rx(-θ) = I (and Ry, Rz)
        if g1.gate_name == g2.gate_name and g1.gate_name in ('Rx', 'Ry', 'Rz', 'Phase'):
            if len(g1.params) == 1 and len(g2.params) == 1:
                if abs(g1.params[0] + g2.params[0]) < 1e-10:
                    return True

        return False

    def _rebuild_circuit(self, original: QuantumCircuit, ops: List[CircuitOperation]) -> QuantumCircuit:
        """Rebuild circuit from operations list."""
        qc = QuantumCircuit(original.n_qubits, original.n_classical, original.name)
        for op in ops:
            qc._operations.append(op)
        return qc


# =============================================================================
# Single-Qubit Fusion Pass
# =============================================================================

class SingleQubitFusion(OptimizationPass):
    """
    Merge consecutive single-qubit gates into a single U3 gate.

    Any sequence of single-qubit gates on the same qubit can be
    combined into a single U3(θ, φ, λ) gate by multiplying their
    matrices. This reduces circuit depth and gate count.

    Example: H · T · H = Ry(π/4) (one gate instead of three)
    """

    SINGLE_QUBIT_GATES = {
        'I', 'X', 'Y', 'Z', 'H', 'S', 'Sdg', 'T', 'Tdg',
        'SX', 'SXdg', 'Rx', 'Ry', 'Rz', 'Phase', 'U1', 'U2', 'U3'
    }

    @property
    def name(self) -> str:
        return "single_qubit_fusion"

    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        ops = list(circuit.operations)
        result_ops = []
        i = 0

        while i < len(ops):
            op = ops[i]

            if (op.op_type == OperationType.GATE and
                    op.operation.gate_name in self.SINGLE_QUBIT_GATES and
                    len(op.operation.qubits) == 1):

                # Collect consecutive single-qubit gates on this qubit
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
                    # Fuse the chain into a single gate
                    fused = self._fuse_chain(chain, qubit)
                    if fused is not None:
                        result_ops.append(fused)
                    i = j
                    continue

            result_ops.append(op)
            i += 1

        qc = QuantumCircuit(circuit.n_qubits, circuit.n_classical, circuit.name)
        for op in result_ops:
            qc._operations.append(op)
        return qc

    def _fuse_chain(self, chain: List[CircuitOperation], qubit: int) -> Optional[CircuitOperation]:
        """Fuse a chain of single-qubit gates into one U3."""
        # Multiply all matrices
        combined = np.eye(2, dtype=complex)
        for op in chain:
            gate = op.operation
            params = gate.params if gate.params else None
            mat = get_gate(gate.gate_name, params)
            combined = mat @ combined

        # Check if result is identity (within tolerance)
        if np.allclose(combined, np.eye(2, dtype=complex), atol=1e-10):
            return None

        # Decompose into U3(θ, φ, λ) parameters
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
        """
        Decompose a 2x2 unitary into ZYZ Euler angles.

        U = e^{iα} Rz(φ) Ry(θ) Rz(λ) = U3(θ, φ, λ)
        """
        # Extract global phase
        det = np.linalg.det(U)
        phase = np.angle(det) / 2
        U_su2 = U * np.exp(-1j * phase)

        # Extract angles
        # U3(θ,φ,λ) = [[cos(θ/2), -e^{iλ}sin(θ/2)],
        #               [e^{iφ}sin(θ/2), e^{i(φ+λ)}cos(θ/2)]]
        theta = 2 * np.arccos(np.clip(np.abs(U_su2[0, 0]), 0, 1))

        if np.abs(np.sin(theta / 2)) < 1e-10:
            # θ ≈ 0: only phase matters
            phi = 0.0
            lam = float(np.angle(U_su2[1, 1]))
        elif np.abs(np.cos(theta / 2)) < 1e-10:
            # θ ≈ π
            phi = float(np.angle(U_su2[1, 0]))
            lam = float(-np.angle(U_su2[0, 1]))
        else:
            phi = float(np.angle(U_su2[1, 0]))
            lam = float(-np.angle(U_su2[0, 1]))

        return float(theta), phi, lam


# =============================================================================
# Commutation Analysis Pass
# =============================================================================

# Gates that commute: [G1, G2] = 0
COMMUTING_PAIRS = {
    # Diagonal gates commute with each other
    frozenset({'Z', 'S', 'Sdg', 'T', 'Tdg', 'Rz', 'Phase', 'CZ'}),
    # X commutes with CX on control
    # Z commutes with CX on target
}


class CommutationAnalysis(OptimizationPass):
    """
    Reorder commuting gates to enable further cancellations.

    Two gates commute if applying them in either order gives the same
    result. By reordering commuting gates, we can bring cancellable
    pairs together for the GateCancellation pass to eliminate.

    Diagonal gates (Z, S, T, Rz, CZ) all commute with each other.
    """

    # Sets of mutually commuting gate names
    DIAGONAL_GATES = {'Z', 'S', 'Sdg', 'T', 'Tdg', 'Rz', 'Phase', 'U1', 'CZ'}

    @property
    def name(self) -> str:
        return "commutation_analysis"

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

        qc = QuantumCircuit(circuit.n_qubits, circuit.n_classical, circuit.name)
        for op in ops:
            qc._operations.append(op)
        return qc

    def _should_swap(self, op1: CircuitOperation, op2: CircuitOperation) -> bool:
        """Determine if swapping two operations is beneficial."""
        if op1.op_type != OperationType.GATE or op2.op_type != OperationType.GATE:
            return False

        g1, g2 = op1.operation, op2.operation

        # Only swap if they commute
        if not self._gates_commute(g1, g2):
            return False

        # Swap if it brings cancellable pairs together
        if g1.gate_name == g2.gate_name and g1.qubits == g2.qubits:
            return False  # Already adjacent, cancellation pass will handle

        # Heuristic: move gates toward same-name neighbors
        return g1.gate_name > g2.gate_name  # Sort by name as simple heuristic

    def _gates_commute(self, g1: GateOperation, g2: GateOperation) -> bool:
        """Check if two gates commute."""
        # Gates on disjoint qubits always commute
        if not set(g1.qubits) & set(g2.qubits):
            return True

        # Diagonal gates commute with each other
        if g1.gate_name in self.DIAGONAL_GATES and g2.gate_name in self.DIAGONAL_GATES:
            return True

        # Same gate on same qubits always commutes with itself
        if g1.gate_name == g2.gate_name and g1.qubits == g2.qubits:
            return True

        # Z commutes with CX on target qubit
        if g1.gate_name == 'Z' and g2.gate_name in ('CX', 'CNOT'):
            if g1.qubits[0] == g2.qubits[1]:  # Z on target of CX
                return True
        if g2.gate_name == 'Z' and g1.gate_name in ('CX', 'CNOT'):
            if g2.qubits[0] == g1.qubits[1]:
                return True

        # X commutes with CX on control qubit
        if g1.gate_name == 'X' and g2.gate_name in ('CX', 'CNOT'):
            if g1.qubits[0] == g2.qubits[0]:  # X on control of CX
                return True
        if g2.gate_name == 'X' and g1.gate_name in ('CX', 'CNOT'):
            if g2.qubits[0] == g1.qubits[0]:
                return True

        return False


# =============================================================================
# CX (CNOT) Optimization Pass
# =============================================================================

class CXOptimization(OptimizationPass):
    """
    Reduce CNOT gate count using circuit identities.

    CNOT gates are the most expensive in many hardware architectures.
    This pass applies known identities:
    - CNOT(a,b)·CNOT(a,b) = I (cancellation)
    - CNOT(a,b)·CNOT(b,a)·CNOT(a,b) = SWAP(a,b) (direction reversal)
    - H⊗H · CNOT(a,b) · H⊗H = CNOT(b,a) (direction flip via Hadamard)
    """

    @property
    def name(self) -> str:
        return "cx_optimization"

    def run(self, circuit: QuantumCircuit) -> QuantumCircuit:
        ops = list(circuit.operations)
        changed = True

        while changed:
            changed = False

            # Pass 1: Cancel adjacent CNOTs
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

            # Pass 2: Detect CNOT-CNOT-CNOT = SWAP pattern and simplify
            new_ops = []
            i = 0
            while i < len(ops):
                if i + 2 < len(ops) and self._is_swap_pattern(ops[i], ops[i + 1], ops[i + 2]):
                    # Replace 3 CNOTs with SWAP
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

        qc = QuantumCircuit(circuit.n_qubits, circuit.n_classical, circuit.name)
        for op in ops:
            qc._operations.append(op)
        return qc

    def _cnots_cancel(self, op1: CircuitOperation, op2: CircuitOperation) -> bool:
        """Check if two CNOTs cancel."""
        if op1.op_type != OperationType.GATE or op2.op_type != OperationType.GATE:
            return False
        g1, g2 = op1.operation, op2.operation
        if g1.gate_name in ('CX', 'CNOT') and g2.gate_name in ('CX', 'CNOT'):
            return g1.qubits == g2.qubits
        return False

    def _is_swap_pattern(self, op1: CircuitOperation, op2: CircuitOperation, op3: CircuitOperation) -> bool:
        """Check for CNOT(a,b)·CNOT(b,a)·CNOT(a,b) = SWAP pattern."""
        if not all(op.op_type == OperationType.GATE for op in [op1, op2, op3]):
            return False

        g1, g2, g3 = op1.operation, op2.operation, op3.operation
        if not all(g.gate_name in ('CX', 'CNOT') for g in [g1, g2, g3]):
            return False

        # Pattern: CX(a,b) CX(b,a) CX(a,b)
        if (g1.qubits == g3.qubits and
                g2.qubits == [g1.qubits[1], g1.qubits[0]]):
            return True

        return False


# =============================================================================
# Rotation Merging Pass
# =============================================================================

class RotationMerging(OptimizationPass):
    """
    Merge adjacent rotation gates on the same axis.

    Rz(α) · Rz(β) = Rz(α + β), and similarly for Rx and Ry.
    Also handles Phase gates: Phase(α) · Phase(β) = Phase(α + β).
    """

    ROTATION_GATES = {'Rx', 'Ry', 'Rz', 'Phase', 'U1'}

    @property
    def name(self) -> str:
        return "rotation_merging"

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

        qc = QuantumCircuit(circuit.n_qubits, circuit.n_classical, circuit.name)
        for op in ops:
            qc._operations.append(op)
        return qc

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

        # Remove if angle is effectively zero (mod 2π)
        if abs(merged_angle % (2 * np.pi)) < 1e-10:
            return None  # Will be skipped

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


# =============================================================================
# Main Optimization Pipeline
# =============================================================================

# Default optimization passes in order
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
    """
    Apply optimization passes to a quantum circuit.

    Runs multiple iterations of the optimization pipeline, since
    each pass can create new opportunities for other passes.

    Args:
        circuit: Circuit to optimize
        passes: List of OptimizationPass classes (uses defaults if None)
        iterations: Number of full pipeline iterations

    Returns:
        OptimizationResult with original and optimized circuits
    """
    from ..analysis.circuit_stats import circuit_depth, gate_count, two_qubit_gate_count

    if passes is None:
        passes = DEFAULT_PASSES

    pass_instances = [p() for p in passes]
    passes_applied = []

    # Calculate original metrics
    orig_depth = circuit_depth(circuit)
    orig_gates = gate_count(circuit)
    orig_total = sum(orig_gates.values())
    orig_cx = two_qubit_gate_count(circuit)

    # Run optimization pipeline
    current = circuit
    for iteration in range(iterations):
        for opt_pass in pass_instances:
            optimized = opt_pass.run(current)
            if len(optimized) != len(current):
                passes_applied.append(f"{opt_pass.name} (iter {iteration + 1})")
            current = optimized

    # Calculate optimized metrics
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


# Export
__all__ = [
    'OptimizationPass',
    'GateCancellation',
    'SingleQubitFusion',
    'CommutationAnalysis',
    'CXOptimization',
    'RotationMerging',
    'optimize_circuit',
    'OptimizationResult',
]
