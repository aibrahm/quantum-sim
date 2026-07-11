"""Tests for DensityMatrix gate and channel application."""

import numpy as np
import pytest
from quantum_simulator.circuit.circuit import QuantumCircuit
from quantum_simulator.circuit.executor import get_statevector


class TestDensityMatrixSimulation:
    """Test that the density matrix path matches the state vector path."""

    def test_density_matrix_matches_statevector(self):
        """Pure state circuit: rho must equal |psi><psi|."""
        from quantum_simulator.circuit.executor import get_density_matrix

        qc = QuantumCircuit(3)
        qc.h(0).cx(0, 1).ry(0.7, 2).ccx(0, 1, 2).rz(0.3, 1).swap(1, 2).t(0)

        sv = get_statevector(qc)
        dm = get_density_matrix(qc)

        expected = np.outer(sv.amplitudes, sv.amplitudes.conj())
        assert np.allclose(dm.rho, expected, atol=1e-10)

    def test_contracted_gate_matches_full_operator(self):
        """Contraction must reproduce U rho U-dagger built from the full operator."""
        from quantum_simulator.core.density_matrix import DensityMatrix
        from quantum_simulator.core.gates import CNOT, multi_qubit_gate

        rng = np.random.default_rng(7)
        vec = rng.normal(size=8) + 1j * rng.normal(size=8)
        dm = DensityMatrix.from_state_vector(vec)

        result = dm.apply_gate(CNOT, [2, 0])

        full = multi_qubit_gate(CNOT, [2, 0], 3)
        expected = full @ dm.rho @ full.conj().T
        assert np.allclose(result.rho, expected, atol=1e-10)

    def test_channel_preserves_trace(self):
        """Kraus channel applied by contraction must keep trace 1."""
        from quantum_simulator.core.density_matrix import DensityMatrix
        from quantum_simulator.core.channels import depolarizing_channel

        dm = DensityMatrix.from_state_vector(np.array([1, 0, 0, 1], dtype=complex))
        noisy = dm.apply_channel(depolarizing_channel(0.2), [1])

        assert abs(np.trace(noisy.rho).real - 1.0) < 1e-10
        assert noisy.purity() < 1.0
