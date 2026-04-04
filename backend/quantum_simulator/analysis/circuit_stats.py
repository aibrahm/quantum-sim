"""
Circuit statistics and analysis.
"""

from typing import Dict, List, Tuple
from collections import defaultdict

from ..circuit.circuit import QuantumCircuit, OperationType, GateOperation


# Two-qubit gate names
TWO_QUBIT_GATES = {
    'CX', 'CNOT', 'CY', 'CZ', 'SWAP', 'iSWAP', 'SQSWAP',
    'CRx', 'CRy', 'CRz', 'CPhase', 'CU',
    'Rxx', 'Ryy', 'Rzz'
}

# Three-qubit gate names
THREE_QUBIT_GATES = {
    'CCX', 'CCNOT', 'TOFFOLI', 'CSWAP', 'FREDKIN', 'CCZ'
}


def gate_count(circuit: QuantumCircuit) -> Dict[str, int]:
    """Count occurrences of each gate type."""
    counts: Dict[str, int] = defaultdict(int)

    for op in circuit.operations:
        if op.op_type == OperationType.GATE:
            counts[op.operation.gate_name] += 1

    return dict(counts)


def two_qubit_gate_count(circuit: QuantumCircuit) -> int:
    """Count two-qubit gates."""
    count = 0
    for op in circuit.operations:
        if op.op_type == OperationType.GATE:
            if op.operation.gate_name in TWO_QUBIT_GATES:
                count += 1
            elif len(op.operation.qubits) == 2:
                count += 1
    return count


def three_qubit_gate_count(circuit: QuantumCircuit) -> int:
    """Count three-qubit gates."""
    count = 0
    for op in circuit.operations:
        if op.op_type == OperationType.GATE:
            if op.operation.gate_name in THREE_QUBIT_GATES:
                count += 1
            elif len(op.operation.qubits) == 3:
                count += 1
    return count


def circuit_depth(circuit: QuantumCircuit) -> int:
    """Calculate circuit depth (longest path through circuit)."""
    if len(circuit) == 0:
        return 0

    # Track depth for each qubit
    qubit_depths = [0] * circuit.n_qubits

    for op in circuit.operations:
        if op.op_type == OperationType.GATE:
            qubits = op.operation.qubits

            # Gate depth is max of involved qubits + 1
            max_depth = max(qubit_depths[q] for q in qubits)
            new_depth = max_depth + 1

            # Update all involved qubits
            for q in qubits:
                qubit_depths[q] = new_depth

        elif op.op_type == OperationType.MEASUREMENT:
            for q in op.operation.qubits:
                qubit_depths[q] += 1

        elif op.op_type == OperationType.BARRIER:
            # Barrier synchronizes qubits
            if op.qubits:
                max_depth = max(qubit_depths[q] for q in op.qubits)
                for q in op.qubits:
                    qubit_depths[q] = max_depth

    return max(qubit_depths)


def critical_path(circuit: QuantumCircuit) -> List[GateOperation]:
    """Find the critical path (longest dependency chain)."""
    if len(circuit) == 0:
        return []

    # Build dependency graph
    gate_ops = [
        (i, op.operation) for i, op in enumerate(circuit.operations)
        if op.op_type == OperationType.GATE
    ]

    if not gate_ops:
        return []

    # Track last operation on each qubit
    last_on_qubit: Dict[int, Tuple[int, GateOperation]] = {}
    predecessors: Dict[int, List[int]] = defaultdict(list)

    for idx, gate in gate_ops:
        for q in gate.qubits:
            if q in last_on_qubit:
                predecessors[idx].append(last_on_qubit[q][0])
            last_on_qubit[q] = (idx, gate)

    # Find longest path using dynamic programming
    depths = {}
    paths = {}

    def get_depth(idx: int) -> int:
        if idx in depths:
            return depths[idx]

        if not predecessors[idx]:
            depths[idx] = 1
            paths[idx] = [idx]
        else:
            max_pred_depth = 0
            max_pred = None
            for pred in predecessors[idx]:
                d = get_depth(pred)
                if d > max_pred_depth:
                    max_pred_depth = d
                    max_pred = pred

            depths[idx] = max_pred_depth + 1
            paths[idx] = paths[max_pred] + [idx] if max_pred is not None else [idx]

        return depths[idx]

    # Find node with maximum depth
    max_depth = 0
    max_idx = None
    for idx, _ in gate_ops:
        d = get_depth(idx)
        if d > max_depth:
            max_depth = d
            max_idx = idx

    if max_idx is None:
        return []

    # Return critical path operations
    return [gate_ops[i][1] for i in paths[max_idx] if i < len(gate_ops)]


def qubit_utilization(circuit: QuantumCircuit) -> Dict[int, float]:
    """Calculate utilization of each qubit (gates / depth)."""
    depth = circuit_depth(circuit)
    if depth == 0:
        return {q: 0.0 for q in range(circuit.n_qubits)}

    qubit_gates = defaultdict(int)
    for op in circuit.operations:
        if op.op_type == OperationType.GATE:
            for q in op.operation.qubits:
                qubit_gates[q] += 1

    return {
        q: qubit_gates[q] / depth
        for q in range(circuit.n_qubits)
    }


def parameter_count(circuit: QuantumCircuit) -> int:
    """Count total number of parameters in circuit."""
    count = 0
    for op in circuit.operations:
        if op.op_type == OperationType.GATE:
            count += len(op.operation.params)
    return count


def circuit_summary(circuit: QuantumCircuit) -> Dict:
    """Circuit statistics summary."""
    gates = gate_count(circuit)

    return {
        'n_qubits': circuit.n_qubits,
        'n_classical': circuit.n_classical,
        'depth': circuit_depth(circuit),
        'total_gates': sum(gates.values()),
        'gate_counts': gates,
        'single_qubit_gates': sum(
            v for k, v in gates.items()
            if k not in TWO_QUBIT_GATES and k not in THREE_QUBIT_GATES
        ),
        'two_qubit_gates': two_qubit_gate_count(circuit),
        'three_qubit_gates': three_qubit_gate_count(circuit),
        'parameters': parameter_count(circuit),
        'measurements': sum(
            1 for op in circuit.operations
            if op.op_type == OperationType.MEASUREMENT
        ),
        'barriers': sum(
            1 for op in circuit.operations
            if op.op_type == OperationType.BARRIER
        ),
    }
