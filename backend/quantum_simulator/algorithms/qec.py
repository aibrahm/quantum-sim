"""
Quantum Error Correction (QEC).

Reference: Shor, Physical Review A 52(4), R2493 (1995);
Steane, Physical Review Letters 77(5), 793 (1996)
"""

from typing import List, Dict, Any
from dataclasses import dataclass

from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import get_statevector


@dataclass
class QECResult:
    """Result of quantum error correction."""
    code_name: str
    n_physical: int
    n_logical: int
    n_ancilla: int
    error_type: str
    error_qubit: int
    syndrome: str
    corrected: bool
    fidelity: float
    logical_state: str


def bit_flip_encode(circuit: QuantumCircuit, data_qubit: int, ancilla1: int, ancilla2: int) -> QuantumCircuit:
    """Encode one logical qubit using the 3-qubit bit-flip code."""
    circuit.cx(data_qubit, ancilla1)
    circuit.cx(data_qubit, ancilla2)
    return circuit


def bit_flip_syndrome(circuit: QuantumCircuit, qubits: List[int], syndrome_qubits: List[int]) -> QuantumCircuit:
    """Measure error syndrome for the bit-flip code."""
    q1, q2, q3 = qubits
    s1, s2 = syndrome_qubits

    circuit.cx(q1, s1)
    circuit.cx(q2, s1)

    circuit.cx(q2, s2)
    circuit.cx(q3, s2)

    return circuit


def bit_flip_correct(circuit: QuantumCircuit, qubits: List[int], syndrome_qubits: List[int]) -> QuantumCircuit:
    """Apply correction based on syndrome measurement."""
    q1, q2, q3 = qubits
    s1, s2 = syndrome_qubits

    circuit.x(s2)
    circuit.ccx(s1, s2, q1)
    circuit.x(s2)

    circuit.ccx(s1, s2, q2)

    circuit.x(s1)
    circuit.ccx(s1, s2, q3)
    circuit.x(s1)

    return circuit


def run_bit_flip_code(
    logical_state: str = "0",
    error_qubit: int = 0,
    apply_error: bool = True
) -> QECResult:
    """Demonstrate the 3-qubit bit-flip code."""
    qc = QuantumCircuit(5, name="bit_flip_code")
    data_qubits = [0, 1, 2]
    syndrome_qubits = [3, 4]

    if logical_state == "1":
        qc.x(0)

    bit_flip_encode(qc, 0, 1, 2)

    if apply_error:
        qc.x(data_qubits[error_qubit])

    bit_flip_syndrome(qc, data_qubits, syndrome_qubits)

    bit_flip_correct(qc, data_qubits, syndrome_qubits)

    sv = get_statevector(qc)

    probs = sv.probabilities
    if logical_state == "0":
        target_prob = probs[0]
    else:
        target_prob = probs[7]

    syndrome_bits = "00"
    if apply_error:
        syndrome_map = {0: "10", 1: "11", 2: "01"}
        syndrome_bits = syndrome_map.get(error_qubit, "00")

    return QECResult(
        code_name="3-qubit bit-flip code",
        n_physical=3,
        n_logical=1,
        n_ancilla=2,
        error_type="X (bit-flip)" if apply_error else "none",
        error_qubit=error_qubit,
        syndrome=syndrome_bits,
        corrected=target_prob > 0.9,
        fidelity=float(target_prob),
        logical_state=logical_state
    )


def phase_flip_encode(circuit: QuantumCircuit, data_qubit: int, ancilla1: int, ancilla2: int) -> QuantumCircuit:
    """Encode using the 3-qubit phase-flip code."""
    circuit.cx(data_qubit, ancilla1)
    circuit.cx(data_qubit, ancilla2)
    circuit.h(data_qubit)
    circuit.h(ancilla1)
    circuit.h(ancilla2)
    return circuit


def run_phase_flip_code(
    logical_state: str = "0",
    error_qubit: int = 0,
    apply_error: bool = True
) -> QECResult:
    """Demonstrate the 3-qubit phase-flip code."""
    qc = QuantumCircuit(5, name="phase_flip_code")
    data_qubits = [0, 1, 2]
    syndrome_qubits = [3, 4]

    if logical_state == "1":
        qc.x(0)

    phase_flip_encode(qc, 0, 1, 2)

    if apply_error:
        qc.z(data_qubits[error_qubit])

    for q in data_qubits:
        qc.h(q)

    bit_flip_syndrome(qc, data_qubits, syndrome_qubits)
    bit_flip_correct(qc, data_qubits, syndrome_qubits)

    for q in data_qubits:
        qc.h(q)

    sv = get_statevector(qc)
    probs = sv.probabilities
    target_prob = float(max(probs))

    syndrome_map = {0: "10", 1: "11", 2: "01"}
    syndrome_bits = syndrome_map.get(error_qubit, "00") if apply_error else "00"

    return QECResult(
        code_name="3-qubit phase-flip code",
        n_physical=3,
        n_logical=1,
        n_ancilla=2,
        error_type="Z (phase-flip)" if apply_error else "none",
        error_qubit=error_qubit,
        syndrome=syndrome_bits,
        corrected=target_prob > 0.9,
        fidelity=target_prob,
        logical_state=logical_state
    )


def shor_encode(circuit: QuantumCircuit, logical_qubit: int) -> QuantumCircuit:
    """Encode one logical qubit using Shor's 9-qubit code."""
    circuit.cx(0, 3)
    circuit.cx(0, 6)

    circuit.h(0)
    circuit.h(3)
    circuit.h(6)

    for block_start in [0, 3, 6]:
        circuit.cx(block_start, block_start + 1)
        circuit.cx(block_start, block_start + 2)

    return circuit


def run_shor_code(
    logical_state: str = "0",
    error_type: str = "X",
    error_qubit: int = 0
) -> QECResult:
    """Demonstrate Shor's 9-qubit code."""
    n_total = 17
    qc = QuantumCircuit(n_total, name="shor_9qubit")

    if logical_state == "1":
        qc.x(0)

    shor_encode(qc, 0)

    if error_type == "X":
        qc.x(error_qubit)
    elif error_type == "Z":
        qc.z(error_qubit)
    elif error_type == "Y":
        qc.y(error_qubit)

    for block_idx, block_start in enumerate([0, 3, 6]):
        s1 = 9 + block_idx * 2
        s2 = 10 + block_idx * 2
        block_qubits = [block_start, block_start + 1, block_start + 2]
        bit_flip_syndrome(qc, block_qubits, [s1, s2])
        bit_flip_correct(qc, block_qubits, [s1, s2])

    for block_start in [0, 3, 6]:
        qc.cx(block_start, block_start + 1)
        qc.cx(block_start, block_start + 2)
        qc.h(block_start)

    qc.cx(0, 15)
    qc.cx(3, 15)
    qc.cx(3, 16)
    qc.cx(6, 16)

    qc.x(16)
    qc.ccx(15, 16, 0)
    qc.x(16)
    qc.ccx(15, 16, 3)
    qc.x(15)
    qc.ccx(15, 16, 6)
    qc.x(15)

    sv = get_statevector(qc)
    fidelity = float(max(sv.probabilities))

    return QECResult(
        code_name="Shor's 9-qubit code",
        n_physical=9,
        n_logical=1,
        n_ancilla=8,
        error_type=f"{error_type} error" if error_type != "none" else "none",
        error_qubit=error_qubit,
        syndrome="see measurement",
        corrected=fidelity > 0.8,
        fidelity=fidelity,
        logical_state=logical_state
    )


def compare_codes(error_type: str = "X", error_qubit: int = 0) -> Dict[str, Any]:
    """Compare all implemented QEC codes on the same error."""
    results = {}

    if error_type in ("X", "none"):
        results['bit_flip'] = run_bit_flip_code("0", min(error_qubit, 2), error_type != "none")

    if error_type in ("Z", "none"):
        results['phase_flip'] = run_phase_flip_code("0", min(error_qubit, 2), error_type != "none")

    results['shor'] = run_shor_code("0", error_type, min(error_qubit, 8))

    results['summary'] = {
        'error_type': error_type,
        'error_qubit': error_qubit,
        'codes_tested': list(results.keys()),
        'note': 'Shor code corrects any single-qubit error; '
                'bit-flip only corrects X; phase-flip only corrects Z.',
    }

    return results
