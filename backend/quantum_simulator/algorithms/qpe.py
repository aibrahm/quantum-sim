"""
Quantum Phase Estimation (QPE).

Estimates the phase theta in U|psi> = e^{2*pi*i*theta}|psi> to n bits of precision.
"""

import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from scipy.linalg import expm

from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import run_circuit, get_statevector, ExecutionResult
from ..core.state_vector import StateVector
from .qft import inverse_qft_on_register


def controlled_unitary_power(
    circuit: QuantumCircuit,
    control: int,
    targets: List[int],
    unitary: np.ndarray,
    power: int
) -> QuantumCircuit:
    """Apply controlled-U^power to the circuit."""
    U_pow = np.linalg.matrix_power(unitary, power)

    if len(targets) == 1:
        theta, phi, lam, phase = _decompose_to_zyz(U_pow)

        if abs(phase) > 1e-10:
            circuit.p(phase, control)

        circuit.rz((lam - phi) / 2, targets[0])
        circuit.cx(control, targets[0])
        circuit.rz(-(phi + lam) / 2, targets[0])
        circuit.ry(-theta / 2, targets[0])
        circuit.cx(control, targets[0])
        circuit.ry(theta / 2, targets[0])
        circuit.rz(phi, targets[0])
    else:
        from ..circuit.circuit import GateOperation, CircuitOperation, OperationType
        gate_op = GateOperation(
            gate_name=f'CU_pow{power}',
            qubits=[control] + targets,
            params=[],
            label=f'c-U^{power}'
        )
        circuit._operations.append(CircuitOperation(
            op_type=OperationType.GATE,
            operation=gate_op,
            qubits=[control] + targets
        ))

    return circuit


def _decompose_to_zyz(U: np.ndarray) -> Tuple[float, float, float, float]:
    """Decompose a 2x2 unitary into ZYZ Euler angles + global phase."""
    det = np.linalg.det(U)
    alpha = np.angle(det) / 2
    U_su2 = U * np.exp(-1j * alpha)

    theta = 2 * np.arccos(np.clip(np.abs(U_su2[0, 0]), 0, 1))

    if abs(np.sin(theta / 2)) < 1e-10:
        phi = 0.0
        lam = float(np.angle(U_su2[1, 1]))
    else:
        phi = float(np.angle(U_su2[1, 0]))
        lam = float(-np.angle(U_su2[0, 1]))

    return float(theta), phi, lam, float(alpha)


def qpe_circuit(
    unitary: np.ndarray,
    n_precision: int,
    n_state: int = 1,
    initial_state: Optional[np.ndarray] = None
) -> QuantumCircuit:
    """Construct a QPE circuit."""
    total_qubits = n_precision + n_state
    qc = QuantumCircuit(total_qubits, n_precision, name="qpe")

    precision_qubits = list(range(n_precision))
    state_qubits = list(range(n_precision, total_qubits))

    for q in precision_qubits:
        qc.h(q)

    if initial_state is not None:
        for i, q in enumerate(state_qubits):
            if i < len(initial_state) and initial_state[i] == 1:
                qc.x(q)

    for k in range(n_precision):
        power = 2 ** k
        control_qubit = precision_qubits[k]
        controlled_unitary_power(qc, control_qubit, state_qubits, unitary, power)

    inverse_qft_on_register(qc, precision_qubits)

    return qc


def run_qpe(
    unitary: np.ndarray,
    n_precision: int = 4,
    eigenstate: Optional[np.ndarray] = None,
    shots: int = 1024
) -> Dict[str, Any]:
    """Run QPE and extract estimated phases."""
    n_state = int(np.log2(unitary.shape[0]))

    initial = None
    if eigenstate is not None:
        initial = [1] + [0] * (n_state - 1)

    qc = qpe_circuit(unitary, n_precision, n_state, initial)

    for i in range(n_precision):
        qc.measure(i, i)

    result = run_circuit(qc, shots=shots)

    n_bins = 2 ** n_precision
    phase_estimates = {}

    for outcome, count in result.counts.items():
        precision_bits = outcome[:n_precision]
        phase_int = int(precision_bits, 2)
        estimated_phase = phase_int / n_bins
        phase_estimates[estimated_phase] = phase_estimates.get(estimated_phase, 0) + count

    phase_probs = {k: v / shots for k, v in phase_estimates.items()}

    eigenvalues = np.linalg.eigvals(unitary)
    true_phases = sorted([float(np.mod(np.angle(ev) / (2 * np.pi), 1.0)) for ev in eigenvalues])

    dominant_phase = max(phase_probs, key=phase_probs.get)

    return {
        'estimated_phases': phase_probs,
        'dominant_phase': dominant_phase,
        'true_phases': true_phases,
        'n_precision': n_precision,
        'phase_resolution': 1.0 / n_bins,
        'counts': result.counts,
        'shots': shots,
    }


def qpe_for_hamiltonian(
    hamiltonian: np.ndarray,
    evolution_time: float = 1.0,
    n_precision: int = 6
) -> Dict[str, Any]:
    """Use QPE to estimate eigenvalues of a Hamiltonian via U = e^{iHt}."""
    U = expm(1j * hamiltonian * evolution_time)

    result = run_qpe(U, n_precision)

    energy_estimates = {}
    for phase, prob in result['estimated_phases'].items():
        energy = 2 * np.pi * phase / evolution_time
        energy_estimates[energy] = prob

    true_eigenvalues = sorted(np.linalg.eigvalsh(hamiltonian).tolist())

    return {
        'energy_estimates': energy_estimates,
        'true_eigenvalues': true_eigenvalues,
        'phase_estimates': result['estimated_phases'],
        'evolution_time': evolution_time,
        'n_precision': n_precision,
    }
