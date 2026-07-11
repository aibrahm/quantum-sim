"""
QuantumCircuit - High-level circuit construction API.
Provides a fluent interface for building quantum circuits.
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json


class OperationType(Enum):
    """Types of operations in a circuit."""
    GATE = "gate"
    MEASUREMENT = "measurement"
    BARRIER = "barrier"
    RESET = "reset"


@dataclass
class GateOperation:
    """Represents a single gate operation in a circuit."""
    gate_name: str
    qubits: List[int]
    params: List[float] = field(default_factory=list)
    controls: List[int] = field(default_factory=list)
    label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'gate_name': self.gate_name,
            'qubits': self.qubits,
            'params': self.params,
            'controls': self.controls,
            'label': self.label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GateOperation':
        return cls(
            gate_name=data['gate_name'],
            qubits=data['qubits'],
            params=data.get('params', []),
            controls=data.get('controls', []),
            label=data.get('label'),
        )


@dataclass
class MeasurementOperation:
    """Represents a measurement operation."""
    qubits: List[int]
    classical_bits: List[int]
    basis: str = 'Z'  # Measurement basis

    def to_dict(self) -> dict:
        return {
            'qubits': self.qubits,
            'classical_bits': self.classical_bits,
            'basis': self.basis,
        }


@dataclass
class CircuitOperation:
    """Generic operation wrapper."""
    op_type: OperationType
    operation: Union[GateOperation, MeasurementOperation, None]
    qubits: List[int] = field(default_factory=list)


class QuantumCircuit:
    """
    Quantum circuit with fluent API for gate application.

    Example:
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1).measure_all()
        result = qc.run(shots=1000)
    """

    def __init__(self, n_qubits: int, n_classical: int = 0, name: str = "circuit"):
        """
        Initialize quantum circuit.

        Args:
            n_qubits: Number of qubits
            n_classical: Number of classical bits (for measurement storage)
            name: Circuit name
        """
        if n_qubits < 1:
            raise ValueError("Must have at least 1 qubit")

        self._n_qubits = n_qubits
        self._n_classical = n_classical if n_classical > 0 else n_qubits
        self._name = name
        self._operations: List[CircuitOperation] = []
        self._metadata: Dict[str, Any] = {}

    @property
    def n_qubits(self) -> int:
        return self._n_qubits

    @property
    def n_classical(self) -> int:
        return self._n_classical

    @property
    def name(self) -> str:
        return self._name

    @property
    def operations(self) -> List[CircuitOperation]:
        return self._operations.copy()

    @property
    def gate_operations(self) -> List[GateOperation]:
        """Get only gate operations."""
        return [
            op.operation for op in self._operations
            if op.op_type == OperationType.GATE
        ]

    def _validate_qubits(self, *qubits: int) -> None:
        """Validate qubit indices."""
        for q in qubits:
            if q < 0 or q >= self._n_qubits:
                raise ValueError(f"Qubit {q} out of range [0, {self._n_qubits})")

    def _add_gate(self, name: str, qubits: List[int],
                  params: List[float] = None, controls: List[int] = None,
                  label: str = None) -> 'QuantumCircuit':
        """Add a gate operation to the circuit."""
        self._validate_qubits(*qubits)
        if controls:
            self._validate_qubits(*controls)

        gate_op = GateOperation(
            gate_name=name,
            qubits=qubits,
            params=params or [],
            controls=controls or [],
            label=label,
        )
        self._operations.append(CircuitOperation(
            op_type=OperationType.GATE,
            operation=gate_op,
            qubits=qubits + (controls or [])
        ))
        return self

    # =========================================================================
    # Single-Qubit Gates
    # =========================================================================

    def i(self, qubit: int) -> 'QuantumCircuit':
        """Identity gate."""
        return self._add_gate('I', [qubit])

    def x(self, qubit: int) -> 'QuantumCircuit':
        """Pauli-X (NOT) gate."""
        return self._add_gate('X', [qubit])

    def y(self, qubit: int) -> 'QuantumCircuit':
        """Pauli-Y gate."""
        return self._add_gate('Y', [qubit])

    def z(self, qubit: int) -> 'QuantumCircuit':
        """Pauli-Z gate."""
        return self._add_gate('Z', [qubit])

    def h(self, qubit: int) -> 'QuantumCircuit':
        """Hadamard gate."""
        return self._add_gate('H', [qubit])

    def s(self, qubit: int) -> 'QuantumCircuit':
        """S gate (sqrt(Z))."""
        return self._add_gate('S', [qubit])

    def sdg(self, qubit: int) -> 'QuantumCircuit':
        """S-dagger gate."""
        return self._add_gate('Sdg', [qubit])

    def t(self, qubit: int) -> 'QuantumCircuit':
        """T gate (sqrt(S))."""
        return self._add_gate('T', [qubit])

    def tdg(self, qubit: int) -> 'QuantumCircuit':
        """T-dagger gate."""
        return self._add_gate('Tdg', [qubit])

    def sx(self, qubit: int) -> 'QuantumCircuit':
        """Sqrt(X) gate."""
        return self._add_gate('SX', [qubit])

    def sxdg(self, qubit: int) -> 'QuantumCircuit':
        """Sqrt(X)-dagger gate."""
        return self._add_gate('SXdg', [qubit])

    # =========================================================================
    # Rotation Gates
    # =========================================================================

    def rx(self, theta: float, qubit: int) -> 'QuantumCircuit':
        """Rotation around X-axis."""
        return self._add_gate('Rx', [qubit], [theta])

    def ry(self, theta: float, qubit: int) -> 'QuantumCircuit':
        """Rotation around Y-axis."""
        return self._add_gate('Ry', [qubit], [theta])

    def rz(self, theta: float, qubit: int) -> 'QuantumCircuit':
        """Rotation around Z-axis."""
        return self._add_gate('Rz', [qubit], [theta])

    def p(self, theta: float, qubit: int) -> 'QuantumCircuit':
        """Phase gate P(θ)."""
        return self._add_gate('Phase', [qubit], [theta])

    def u1(self, lam: float, qubit: int) -> 'QuantumCircuit':
        """U1 gate (equivalent to P)."""
        return self._add_gate('U1', [qubit], [lam])

    def u2(self, phi: float, lam: float, qubit: int) -> 'QuantumCircuit':
        """U2 gate."""
        return self._add_gate('U2', [qubit], [phi, lam])

    def u3(self, theta: float, phi: float, lam: float, qubit: int) -> 'QuantumCircuit':
        """U3 gate (universal single-qubit gate)."""
        return self._add_gate('U3', [qubit], [theta, phi, lam])

    def u(self, theta: float, phi: float, lam: float, qubit: int,
          gamma: float = 0) -> 'QuantumCircuit':
        """General U gate with global phase."""
        return self._add_gate('U', [qubit], [theta, phi, lam, gamma])

    # =========================================================================
    # Two-Qubit Gates
    # =========================================================================

    def cx(self, control: int, target: int) -> 'QuantumCircuit':
        """CNOT (controlled-X) gate."""
        return self._add_gate('CX', [control, target])

    def cnot(self, control: int, target: int) -> 'QuantumCircuit':
        """Alias for cx."""
        return self.cx(control, target)

    def cy(self, control: int, target: int) -> 'QuantumCircuit':
        """Controlled-Y gate."""
        return self._add_gate('CY', [control, target])

    def cz(self, control: int, target: int) -> 'QuantumCircuit':
        """Controlled-Z gate."""
        return self._add_gate('CZ', [control, target])

    def swap(self, qubit1: int, qubit2: int) -> 'QuantumCircuit':
        """SWAP gate."""
        return self._add_gate('SWAP', [qubit1, qubit2])

    def iswap(self, qubit1: int, qubit2: int) -> 'QuantumCircuit':
        """iSWAP gate."""
        return self._add_gate('iSWAP', [qubit1, qubit2])

    def crx(self, theta: float, control: int, target: int) -> 'QuantumCircuit':
        """Controlled rotation around X."""
        return self._add_gate('CRx', [control, target], [theta])

    def cry(self, theta: float, control: int, target: int) -> 'QuantumCircuit':
        """Controlled rotation around Y."""
        return self._add_gate('CRy', [control, target], [theta])

    def crz(self, theta: float, control: int, target: int) -> 'QuantumCircuit':
        """Controlled rotation around Z."""
        return self._add_gate('CRz', [control, target], [theta])

    def cp(self, theta: float, control: int, target: int) -> 'QuantumCircuit':
        """Controlled phase gate."""
        return self._add_gate('CPhase', [control, target], [theta])

    def cu(self, theta: float, phi: float, lam: float,
           control: int, target: int, gamma: float = 0) -> 'QuantumCircuit':
        """Controlled-U gate."""
        return self._add_gate('CU', [control, target], [theta, phi, lam, gamma])

    def rxx(self, theta: float, qubit1: int, qubit2: int) -> 'QuantumCircuit':
        """XX rotation (Ising coupling)."""
        return self._add_gate('Rxx', [qubit1, qubit2], [theta])

    def ryy(self, theta: float, qubit1: int, qubit2: int) -> 'QuantumCircuit':
        """YY rotation (Ising coupling)."""
        return self._add_gate('Ryy', [qubit1, qubit2], [theta])

    def rzz(self, theta: float, qubit1: int, qubit2: int) -> 'QuantumCircuit':
        """ZZ rotation (Ising coupling)."""
        return self._add_gate('Rzz', [qubit1, qubit2], [theta])

    # =========================================================================
    # Three-Qubit Gates
    # =========================================================================

    def ccx(self, control1: int, control2: int, target: int) -> 'QuantumCircuit':
        """Toffoli (CCNOT) gate."""
        return self._add_gate('CCX', [control1, control2, target])

    def toffoli(self, control1: int, control2: int, target: int) -> 'QuantumCircuit':
        """Alias for ccx."""
        return self.ccx(control1, control2, target)

    def cswap(self, control: int, target1: int, target2: int) -> 'QuantumCircuit':
        """Fredkin (CSWAP) gate."""
        return self._add_gate('CSWAP', [control, target1, target2])

    def fredkin(self, control: int, target1: int, target2: int) -> 'QuantumCircuit':
        """Alias for cswap."""
        return self.cswap(control, target1, target2)

    # =========================================================================
    # Measurement and Control Flow
    # =========================================================================

    def measure(self, qubit: int, classical_bit: int, basis: str = 'Z') -> 'QuantumCircuit':
        """
        Measure a single qubit.

        Args:
            qubit: Qubit to measure
            classical_bit: Classical bit to store result
            basis: Measurement basis ('X', 'Y', or 'Z')
        """
        self._validate_qubits(qubit)
        if classical_bit < 0 or classical_bit >= self._n_classical:
            raise ValueError(f"Classical bit {classical_bit} out of range")

        measure_op = MeasurementOperation(
            qubits=[qubit],
            classical_bits=[classical_bit],
            basis=basis
        )
        self._operations.append(CircuitOperation(
            op_type=OperationType.MEASUREMENT,
            operation=measure_op,
            qubits=[qubit]
        ))
        return self

    def measure_all(self, basis: str = 'Z') -> 'QuantumCircuit':
        """Measure all qubits."""
        for i in range(self._n_qubits):
            self.measure(i, i, basis)
        return self

    def barrier(self, *qubits: int) -> 'QuantumCircuit':
        """
        Add barrier (visual separator, prevents optimization across).

        Args:
            *qubits: Specific qubits (default: all)
        """
        if not qubits:
            qubits = tuple(range(self._n_qubits))
        self._validate_qubits(*qubits)

        self._operations.append(CircuitOperation(
            op_type=OperationType.BARRIER,
            operation=None,
            qubits=list(qubits)
        ))
        return self

    def reset(self, qubit: int) -> 'QuantumCircuit':
        """Reset qubit to |0⟩."""
        self._validate_qubits(qubit)
        self._operations.append(CircuitOperation(
            op_type=OperationType.RESET,
            operation=None,
            qubits=[qubit]
        ))
        return self

    # =========================================================================
    # Circuit Composition
    # =========================================================================

    def compose(self, other: 'QuantumCircuit', qubits: Optional[List[int]] = None) -> 'QuantumCircuit':
        """
        Compose with another circuit.

        Args:
            other: Circuit to append
            qubits: Qubit mapping (default: identity)

        Returns:
            Self for chaining
        """
        if qubits is None:
            qubits = list(range(other.n_qubits))

        if len(qubits) != other.n_qubits:
            raise ValueError("Qubit mapping length mismatch")

        for op in other._operations:
            if op.op_type == OperationType.GATE:
                gate_op = op.operation
                mapped_qubits = [qubits[q] for q in gate_op.qubits]
                self._add_gate(
                    gate_op.gate_name,
                    mapped_qubits,
                    gate_op.params,
                    gate_op.controls,
                    gate_op.label
                )
            elif op.op_type == OperationType.BARRIER:
                mapped_qubits = [qubits[q] for q in op.qubits]
                self.barrier(*mapped_qubits)
            elif op.op_type == OperationType.RESET:
                for q in op.qubits:
                    self.reset(qubits[q])

        return self

    def inverse(self) -> 'QuantumCircuit':
        """
        Create inverse circuit (gates applied in reverse order with conjugate).
        Only works for unitary gates (no measurements).
        """
        inverse_qc = QuantumCircuit(self._n_qubits, self._n_classical, f"{self._name}_inv")

        # Reverse order
        for op in reversed(self._operations):
            if op.op_type != OperationType.GATE:
                continue

            gate_op = op.operation

            # Get inverse gate name
            inverse_name = self._get_inverse_gate(gate_op.gate_name)
            inverse_params = self._get_inverse_params(gate_op.gate_name, gate_op.params)

            inverse_qc._add_gate(
                inverse_name,
                gate_op.qubits,
                inverse_params,
                gate_op.controls
            )

        return inverse_qc

    def _get_inverse_gate(self, name: str) -> str:
        """Get inverse gate name."""
        inverses = {
            'S': 'Sdg', 'Sdg': 'S',
            'T': 'Tdg', 'Tdg': 'T',
            'SX': 'SXdg', 'SXdg': 'SX',
        }
        return inverses.get(name, name)

    def _get_inverse_params(self, name: str, params: List[float]) -> List[float]:
        """Get inverse gate parameters."""
        if name in ['Rx', 'Ry', 'Rz', 'Phase', 'U1', 'CRx', 'CRy', 'CRz', 'CPhase',
                    'Rxx', 'Ryy', 'Rzz']:
            return [-p for p in params]
        return params

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict:
        """Serialize circuit to dictionary."""
        ops = []
        for op in self._operations:
            op_dict = {
                'type': op.op_type.value,
                'qubits': op.qubits,
            }
            if op.operation:
                op_dict['operation'] = op.operation.to_dict()
            ops.append(op_dict)

        return {
            'n_qubits': self._n_qubits,
            'n_classical': self._n_classical,
            'name': self._name,
            'operations': ops,
            'metadata': self._metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'QuantumCircuit':
        """Deserialize circuit from dictionary."""
        qc = cls(
            data['n_qubits'],
            data.get('n_classical', data['n_qubits']),
            data.get('name', 'circuit')
        )
        qc._metadata = data.get('metadata', {})

        for op_data in data['operations']:
            op_type = OperationType(op_data['type'])

            if op_type == OperationType.GATE:
                gate_op = GateOperation.from_dict(op_data['operation'])
                qc._add_gate(
                    gate_op.gate_name,
                    gate_op.qubits,
                    gate_op.params,
                    gate_op.controls,
                    gate_op.label
                )
            elif op_type == OperationType.MEASUREMENT:
                m_op = op_data['operation']
                for q, c in zip(m_op['qubits'], m_op['classical_bits']):
                    qc.measure(q, c, m_op.get('basis', 'Z'))
            elif op_type == OperationType.BARRIER:
                qc.barrier(*op_data['qubits'])
            elif op_type == OperationType.RESET:
                for q in op_data['qubits']:
                    qc.reset(q)

        return qc

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'QuantumCircuit':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def to_openqasm(self, version: str = "2.0") -> str:
        """
        Export circuit to OpenQASM format.

        Args:
            version: QASM version ("2.0" or "3.0")

        Returns:
            OpenQASM string
        """
        lines = []

        if version == "2.0":
            lines.append("OPENQASM 2.0;")
            lines.append('include "qelib1.inc";')
            lines.append(f"qreg q[{self._n_qubits}];")
            lines.append(f"creg c[{self._n_classical}];")
        else:
            lines.append("OPENQASM 3.0;")
            lines.append(f"qubit[{self._n_qubits}] q;")
            lines.append(f"bit[{self._n_classical}] c;")

        lines.append("")

        gate_map = {
            'I': 'id', 'X': 'x', 'Y': 'y', 'Z': 'z',
            'H': 'h', 'S': 's', 'Sdg': 'sdg', 'T': 't', 'Tdg': 'tdg',
            'SX': 'sx', 'SXdg': 'sxdg',
            'Rx': 'rx', 'Ry': 'ry', 'Rz': 'rz',
            'Phase': 'p', 'U1': 'u1', 'U2': 'u2', 'U3': 'u3',
            'CX': 'cx', 'CY': 'cy', 'CZ': 'cz',
            'SWAP': 'swap', 'CCX': 'ccx', 'CSWAP': 'cswap',
            'CRx': 'crx', 'CRy': 'cry', 'CRz': 'crz', 'CPhase': 'cp',
        }

        for op in self._operations:
            if op.op_type == OperationType.GATE:
                gate = op.operation
                qasm_gate = gate_map.get(gate.gate_name, gate.gate_name.lower())

                if gate.params:
                    param_str = ','.join(f"{p:.10f}" for p in gate.params)
                    qubit_str = ','.join(f"q[{q}]" for q in gate.qubits)
                    lines.append(f"{qasm_gate}({param_str}) {qubit_str};")
                else:
                    qubit_str = ','.join(f"q[{q}]" for q in gate.qubits)
                    lines.append(f"{qasm_gate} {qubit_str};")

            elif op.op_type == OperationType.MEASUREMENT:
                m_op = op.operation
                for q, c in zip(m_op.qubits, m_op.classical_bits):
                    lines.append(f"measure q[{q}] -> c[{c}];")

            elif op.op_type == OperationType.BARRIER:
                qubit_str = ','.join(f"q[{q}]" for q in op.qubits)
                lines.append(f"barrier {qubit_str};")

            elif op.op_type == OperationType.RESET:
                for q in op.qubits:
                    lines.append(f"reset q[{q}];")

        return '\n'.join(lines)

    def __str__(self) -> str:
        return f"QuantumCircuit({self._n_qubits} qubits, {len(self._operations)} operations)"

    def __repr__(self) -> str:
        return self.__str__()

    def __len__(self) -> int:
        """Number of operations."""
        return len(self._operations)


# Export
__all__ = ['QuantumCircuit', 'GateOperation', 'MeasurementOperation',
           'CircuitOperation', 'OperationType']
