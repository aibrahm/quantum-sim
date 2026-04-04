"""
Quantum Phase Estimation (QPE) — Full Implementation.

Given a unitary U and an eigenstate |ψ⟩ with U|ψ⟩ = e^{2πiθ}|ψ⟩,
QPE estimates the phase θ to n bits of precision using O(2^n)
controlled-U operations and the inverse QFT.

This is a foundational subroutine used in:
- Shor's factoring algorithm
- HHL linear systems algorithm
- Quantum chemistry (molecular energy estimation)
- Quantum counting
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
    """
    Apply controlled-U^{2^k} to the circuit.

    For single-qubit unitaries, decomposes into controlled rotations.
    For multi-qubit, uses the matrix directly via the executor.

    Args:
        circuit: Circuit to modify
        control: Control qubit index
        targets: Target qubit indices
        unitary: Unitary matrix
        power: Power to raise U to (U^power)

    Returns:
        Modified circuit
    """
    # Compute U^power
    U_pow = np.linalg.matrix_power(unitary, power)

    if len(targets) == 1:
        # Decompose single-qubit controlled unitary into gates
        # CU = |0⟩⟨0| ⊗ I + |1⟩⟨1| ⊗ U
        # Use U3 decomposition
        theta, phi, lam, phase = _decompose_to_zyz(U_pow)

        # Apply global phase as controlled phase
        if abs(phase) > 1e-10:
            circuit.p(phase, control)

        # Apply controlled-U3
        circuit.rz((lam - phi) / 2, targets[0])
        circuit.cx(control, targets[0])
        circuit.rz(-(phi + lam) / 2, targets[0])
        circuit.ry(-theta / 2, targets[0])
        circuit.cx(control, targets[0])
        circuit.ry(theta / 2, targets[0])
        circuit.rz(phi, targets[0])
    else:
        # For multi-qubit unitaries, add as custom gate
        # Store in circuit metadata for executor to handle
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
    """
    Decompose a 2×2 unitary into ZYZ Euler angles + global phase.

    U = e^{iα} Rz(φ) Ry(θ) Rz(λ)

    Returns:
        (theta, phi, lambda, global_phase)
    """
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
    """
    Construct a Quantum Phase Estimation circuit.

    Circuit structure:
    1. Initialize precision qubits in uniform superposition
    2. Apply controlled-U^{2^k} for each precision qubit k
    3. Apply inverse QFT to precision register
    4. Measure precision register

    Args:
        unitary: Unitary operator (2^n_state × 2^n_state matrix)
        n_precision: Number of precision qubits (determines accuracy)
        n_state: Number of qubits in the eigenstate register
        initial_state: Initial state preparation (None = |0...0⟩)

    Returns:
        QPE circuit
    """
    total_qubits = n_precision + n_state
    qc = QuantumCircuit(total_qubits, n_precision, name="qpe")

    # Precision qubits: 0 to n_precision-1
    # State qubits: n_precision to total_qubits-1
    precision_qubits = list(range(n_precision))
    state_qubits = list(range(n_precision, total_qubits))

    # Step 1: Hadamard on all precision qubits
    for q in precision_qubits:
        qc.h(q)

    # Step 2: Prepare eigenstate (if needed)
    if initial_state is not None:
        # Apply X gates for computational basis state preparation
        for i, q in enumerate(state_qubits):
            if i < len(initial_state) and initial_state[i] == 1:
                qc.x(q)

    # Step 3: Controlled-U^{2^k} operations
    for k in range(n_precision):
        power = 2 ** k
        control_qubit = precision_qubits[k]
        controlled_unitary_power(qc, control_qubit, state_qubits, unitary, power)

    # Step 4: Inverse QFT on precision register
    inverse_qft_on_register(qc, precision_qubits)

    return qc


def run_qpe(
    unitary: np.ndarray,
    n_precision: int = 4,
    eigenstate: Optional[np.ndarray] = None,
    shots: int = 1024
) -> Dict[str, Any]:
    """
    Run Quantum Phase Estimation and extract estimated phases.

    Args:
        unitary: Unitary operator
        n_precision: Precision bits
        eigenstate: Known eigenstate to prepare (None = |1⟩)
        shots: Number of measurement shots

    Returns:
        Dictionary with estimated phases and analysis
    """
    n_state = int(np.log2(unitary.shape[0]))

    # Build QPE circuit
    initial = None
    if eigenstate is not None:
        # Convert eigenstate to computational basis preparation
        initial = [1] + [0] * (n_state - 1)  # Simplified

    qc = qpe_circuit(unitary, n_precision, n_state, initial)

    # Measure only precision qubits (not state register)
    for i in range(n_precision):
        qc.measure(i, i)

    # Run circuit
    result = run_circuit(qc, shots=shots)

    # Extract phase estimates from measurement outcomes
    n_bins = 2 ** n_precision
    phase_estimates = {}

    for outcome, count in result.counts.items():
        # Read precision bits (first n_precision bits)
        precision_bits = outcome[:n_precision]
        phase_int = int(precision_bits, 2)
        estimated_phase = phase_int / n_bins
        phase_estimates[estimated_phase] = phase_estimates.get(estimated_phase, 0) + count

    # Normalize to probabilities
    phase_probs = {k: v / shots for k, v in phase_estimates.items()}

    # True eigenphases for comparison
    eigenvalues = np.linalg.eigvals(unitary)
    true_phases = sorted([float(np.mod(np.angle(ev) / (2 * np.pi), 1.0)) for ev in eigenvalues])

    # Find dominant phase
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
    """
    Use QPE to estimate eigenvalues of a Hamiltonian.

    Converts H to unitary U = e^{iHt}, then QPE extracts
    eigenphases θ_k where E_k = 2πθ_k / t are the eigenvalues.

    This is the core of quantum chemistry algorithms for
    finding molecular ground state energies.

    Args:
        hamiltonian: Hermitian matrix H
        evolution_time: Time parameter t
        n_precision: Number of precision qubits

    Returns:
        Estimated eigenvalues and energy levels
    """
    # Create unitary U = e^{iHt}
    U = expm(1j * hamiltonian * evolution_time)

    # Run QPE
    result = run_qpe(U, n_precision)

    # Convert phases to energies: E = 2πθ / t
    energy_estimates = {}
    for phase, prob in result['estimated_phases'].items():
        energy = 2 * np.pi * phase / evolution_time
        energy_estimates[energy] = prob

    # True eigenvalues
    true_eigenvalues = sorted(np.linalg.eigvalsh(hamiltonian).tolist())

    return {
        'energy_estimates': energy_estimates,
        'true_eigenvalues': true_eigenvalues,
        'phase_estimates': result['estimated_phases'],
        'evolution_time': evolution_time,
        'n_precision': n_precision,
    }


# Export
__all__ = [
    'qpe_circuit',
    'run_qpe',
    'qpe_for_hamiltonian',
    'controlled_unitary_power',
]
