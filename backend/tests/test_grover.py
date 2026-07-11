"""Tests for Grover's search algorithm."""

import numpy as np
import pytest
from quantum_simulator.algorithms.grover import (
    grover_circuit, create_oracle, create_diffusion, optimal_iterations, run_grover
)
from quantum_simulator.circuit.executor import get_statevector


class TestGroverOracle:
    """Test the phase oracle from first principles."""

    @pytest.mark.parametrize("n_qubits,marked", [(2, 1), (3, 5), (4, 9), (5, 19)])
    def test_oracle_flips_only_marked_state(self, n_qubits, marked):
        """Oracle applied to |s> must negate exactly the marked amplitude."""
        from quantum_simulator.circuit.circuit import QuantumCircuit

        qc = QuantumCircuit(n_qubits)
        for q in range(n_qubits):
            qc.h(q)
        qc.compose(create_oracle(n_qubits, [marked]))

        sv = get_statevector(qc)
        amps = sv.amplitudes
        # Remove any global phase using an unmarked reference amplitude
        ref = 0 if marked != 0 else 1
        amps = amps / (amps[ref] * np.sqrt(2 ** n_qubits))

        expected = np.full(2 ** n_qubits, 1 / np.sqrt(2 ** n_qubits), dtype=complex)
        expected[marked] *= -1
        expected /= expected[ref] * np.sqrt(2 ** n_qubits)

        assert np.allclose(amps, expected, atol=1e-10)


class TestGroverSearch:
    """Test full Grover search success probability."""

    @pytest.mark.parametrize("n_qubits", [2, 3, 4, 5])
    def test_marked_state_probability(self, n_qubits):
        """After the optimal iteration count the marked state dominates."""
        marked = (1 << n_qubits) - 2

        qc = grover_circuit(n_qubits, [marked])
        sv = get_statevector(qc)
        prob = float(np.abs(sv.amplitudes[marked]) ** 2)

        # Exact theory: sin^2((2k+1) * asin(1/sqrt(N))) with k optimal
        theta = np.arcsin(1 / np.sqrt(2 ** n_qubits))
        k = optimal_iterations(n_qubits, 1)
        expected = np.sin((2 * k + 1) * theta) ** 2

        assert prob > 0.9
        assert abs(prob - expected) < 1e-8

    @pytest.mark.parametrize("marked", [0, 7, 12])
    def test_arbitrary_marked_state_n4(self, marked):
        """Any marked state should be amplified, not just the all-ones state."""
        qc = grover_circuit(4, [marked])
        sv = get_statevector(qc)
        prob = float(np.abs(sv.amplitudes[marked]) ** 2)
        assert prob > 0.9

    def test_run_grover_sampling(self):
        """Sampled counts should agree with the amplified probability."""
        _, success_prob = run_grover(4, [11], shots=2048)
        assert success_prob > 0.9
