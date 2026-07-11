"""
Quantum Teleportation Implementation.
Transfers quantum state using entanglement and classical communication.
"""

import numpy as np
from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import run_circuit, get_statevector


def teleportation_circuit(theta: float = 0, phi: float = 0) -> QuantumCircuit:
    """
    Create quantum teleportation circuit.

    Teleports a state |ψ⟩ = cos(θ/2)|0⟩ + e^(iφ)sin(θ/2)|1⟩ from qubit 0 to qubit 2.

    Args:
        theta: Bloch sphere polar angle (0 to π)
        phi: Bloch sphere azimuthal angle (0 to 2π)

    Returns:
        Teleportation circuit (3 qubits)
    """
    qc = QuantumCircuit(3, 3, name="teleportation")

    # Prepare state to teleport on qubit 0
    # |ψ⟩ = cos(θ/2)|0⟩ + e^(iφ)sin(θ/2)|1⟩
    if theta != 0:
        qc.ry(theta, 0)  # Rotate from |0⟩
    if phi != 0:
        qc.rz(phi, 0)  # Add phase

    # Create Bell pair between qubits 1 and 2
    qc.h(1)
    qc.cx(1, 2)

    # Bell measurement on qubits 0 and 1
    qc.cx(0, 1)
    qc.h(0)

    # Measure qubits 0 and 1
    qc.measure(0, 0)
    qc.measure(1, 1)

    # Conditional operations on qubit 2 based on measurement
    # In a real circuit, these would be classically controlled
    # Here we apply all corrections (simulating post-selection)
    qc.cx(1, 2)  # If qubit 1 measured |1⟩
    qc.cz(0, 2)  # If qubit 0 measured |1⟩

    return qc


def run_teleportation(
    theta: float = 0,
    phi: float = 0,
    shots: int = 1024
) -> dict:
    """
    Run quantum teleportation and verify fidelity.

    Args:
        theta: Polar angle for state to teleport
        phi: Azimuthal angle for state to teleport

    Returns:
        Dictionary with teleportation results
    """
    # Calculate expected Bloch vector for input state
    x_in = np.sin(theta) * np.cos(phi)
    y_in = np.sin(theta) * np.sin(phi)
    z_in = np.cos(theta)

    # Create and run circuit
    qc = teleportation_circuit(theta, phi)
    result = run_circuit(qc, shots=shots)

    # Get final state vector (without measurements for analysis)
    qc_no_measure = QuantumCircuit(3, name="teleport_analysis")
    if theta != 0:
        qc_no_measure.ry(theta, 0)
    if phi != 0:
        qc_no_measure.rz(phi, 0)
    qc_no_measure.h(1)
    qc_no_measure.cx(1, 2)
    qc_no_measure.cx(0, 1)
    qc_no_measure.h(0)
    # Apply corrections assuming |00⟩ measurement outcome
    qc_no_measure.cx(1, 2)
    qc_no_measure.cz(0, 2)

    sv = get_statevector(qc_no_measure)
    bloch_vectors = sv.all_bloch_vectors()

    # Qubit 2 should have the teleported state
    x_out, y_out, z_out = bloch_vectors[2]

    # Calculate fidelity (simplified - based on Bloch vector overlap)
    fidelity = 0.5 * (1 + x_in * x_out + y_in * y_out + z_in * z_out)

    return {
        "input_state": {
            "theta": theta,
            "phi": phi,
            "bloch": {"x": x_in, "y": y_in, "z": z_in}
        },
        "output_state": {
            "bloch": {"x": x_out, "y": y_out, "z": z_out}
        },
        "fidelity": fidelity,
        "counts": result.counts,
        "shots": shots,
    }


__all__ = [
    'teleportation_circuit',
    'run_teleportation',
]
