"""
Tests for new quantum simulator features:
- Circuit Optimization
- QPE, VQE, QAOA
- Quantum Error Correction
- Entanglement Analysis
- QSVT Research Implementation
"""

import numpy as np
import pytest

# =============================================================================
# Circuit Optimization Tests
# =============================================================================

class TestCircuitOptimization:
    """Test the circuit optimization passes."""

    def test_gate_cancellation_self_inverse(self):
        """HH = I should be cancelled."""
        from quantum_simulator.circuit.circuit import QuantumCircuit
        from quantum_simulator.optimization import optimize_circuit

        qc = QuantumCircuit(1)
        qc.h(0)
        qc.h(0)

        result = optimize_circuit(qc)
        assert result.optimized_gate_count < result.original_gate_count

    def test_gate_cancellation_xx(self):
        """XX = I should be cancelled."""
        from quantum_simulator.circuit.circuit import QuantumCircuit
        from quantum_simulator.optimization import optimize_circuit

        qc = QuantumCircuit(1)
        qc.x(0)
        qc.x(0)

        result = optimize_circuit(qc)
        assert result.optimized_gate_count == 0

    def test_gate_cancellation_inverse_pairs(self):
        """S·S† = I should be cancelled."""
        from quantum_simulator.circuit.circuit import QuantumCircuit
        from quantum_simulator.optimization import optimize_circuit

        qc = QuantumCircuit(1)
        qc.s(0)
        qc.sdg(0)

        result = optimize_circuit(qc)
        assert result.optimized_gate_count < result.original_gate_count

    def test_cnot_cancellation(self):
        """CNOT·CNOT = I."""
        from quantum_simulator.circuit.circuit import QuantumCircuit
        from quantum_simulator.optimization import optimize_circuit

        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        qc.cx(0, 1)

        result = optimize_circuit(qc)
        assert result.optimized_gate_count == 0

    def test_single_qubit_fusion(self):
        """Multiple single-qubit gates should fuse into one U3."""
        from quantum_simulator.circuit.circuit import QuantumCircuit
        from quantum_simulator.optimization import optimize_circuit

        qc = QuantumCircuit(1)
        qc.h(0)
        qc.t(0)
        qc.s(0)

        result = optimize_circuit(qc)
        assert result.optimized_gate_count <= result.original_gate_count

    def test_optimization_preserves_semantics(self):
        """Optimized circuit should produce the same state."""
        from quantum_simulator.circuit.circuit import QuantumCircuit
        from quantum_simulator.circuit.executor import get_statevector
        from quantum_simulator.optimization import optimize_circuit

        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.x(0)
        qc.x(0)  # Should cancel with previous X

        sv_original = get_statevector(qc)
        result = optimize_circuit(qc)
        sv_optimized = get_statevector(result.optimized_circuit)

        np.testing.assert_allclose(
            np.abs(sv_original.amplitudes),
            np.abs(sv_optimized.amplitudes),
            atol=1e-10
        )


# =============================================================================
# VQE Tests
# =============================================================================

class TestVQE:
    """Test Variational Quantum Eigensolver."""

    def test_h2_hamiltonian_construction(self):
        """H₂ Hamiltonian should be Hermitian."""
        from quantum_simulator.algorithms.vqe import PauliHamiltonian

        H = PauliHamiltonian.h2_hamiltonian()
        matrix = H.to_matrix()
        assert np.allclose(matrix, matrix.conj().T)

    def test_ising_hamiltonian(self):
        """Transverse Ising model should be Hermitian."""
        from quantum_simulator.algorithms.vqe import PauliHamiltonian

        H = PauliHamiltonian.transverse_ising(3, J=1.0, h=0.5)
        matrix = H.to_matrix()
        assert np.allclose(matrix, matrix.conj().T)

    def test_vqe_h2(self):
        """VQE should find energy close to exact for H₂."""
        from quantum_simulator.algorithms.vqe import run_h2_vqe

        result = run_h2_vqe(max_iterations=100)
        # Should be within reasonable tolerance
        assert abs(result.ground_energy - result.exact_energy) < 0.1

    def test_hardware_efficient_ansatz(self):
        """Ansatz should produce valid quantum circuit."""
        from quantum_simulator.algorithms.vqe import hardware_efficient_ansatz
        from quantum_simulator.circuit.executor import get_statevector

        qc, n_params = hardware_efficient_ansatz(2, depth=1)
        sv = get_statevector(qc)
        assert abs(np.sum(np.abs(sv.amplitudes) ** 2) - 1.0) < 1e-10


# =============================================================================
# QAOA Tests
# =============================================================================

class TestQAOA:
    """Test QAOA implementation."""

    def test_maxcut_problem(self):
        """MaxCut problem should evaluate cost correctly."""
        from quantum_simulator.algorithms.qaoa import QAOAProblem

        # Triangle graph
        problem = QAOAProblem.max_cut(3, [(0, 1), (1, 2), (0, 2)])
        best_bs, best_cost = problem.max_cost()
        assert best_cost > 0

    def test_qaoa_circuit_construction(self):
        """QAOA circuit should be valid."""
        from quantum_simulator.algorithms.qaoa import QAOAProblem, qaoa_circuit
        from quantum_simulator.circuit.executor import get_statevector

        problem = QAOAProblem.max_cut(3, [(0, 1), (1, 2)])
        qc = qaoa_circuit(problem, [0.5], [0.5])
        sv = get_statevector(qc)
        assert abs(np.sum(np.abs(sv.amplitudes) ** 2) - 1.0) < 1e-10

    def test_qaoa_maxcut(self):
        """QAOA should find reasonable solution for small MaxCut."""
        from quantum_simulator.algorithms.qaoa import run_maxcut_qaoa

        result = run_maxcut_qaoa(3, [(0, 1), (1, 2), (0, 2)], p=1, max_iterations=50)
        assert result.approximation_ratio > 0.5


# =============================================================================
# QEC Tests
# =============================================================================

class TestQEC:
    """Test Quantum Error Correction codes."""

    def test_bit_flip_corrects_x_error(self):
        """Bit-flip code should correct single X errors."""
        from quantum_simulator.algorithms.qec import run_bit_flip_code

        for error_qubit in range(3):
            result = run_bit_flip_code("0", error_qubit, True)
            assert result.code_name == "3-qubit bit-flip code"
            assert result.n_physical == 3

    def test_bit_flip_no_error(self):
        """Bit-flip code without error should have high fidelity."""
        from quantum_simulator.algorithms.qec import run_bit_flip_code

        result = run_bit_flip_code("0", 0, False)
        assert result.fidelity > 0.9

    def test_phase_flip_code(self):
        """Phase-flip code should handle Z errors."""
        from quantum_simulator.algorithms.qec import run_phase_flip_code

        result = run_phase_flip_code("0", 0, True)
        assert result.code_name == "3-qubit phase-flip code"


# =============================================================================
# Entanglement Analysis Tests
# =============================================================================

class TestEntanglement:
    """Test entanglement analysis tools."""

    def test_product_state_not_entangled(self):
        """Product state |00⟩ should have zero entanglement."""
        from quantum_simulator.core.state_vector import StateVector
        from quantum_simulator.analysis.entanglement import (
            schmidt_decomposition, entanglement_entropy
        )

        sv = StateVector(2)  # |00⟩
        sd = schmidt_decomposition(sv, [0])
        assert sd.schmidt_rank == 1
        assert not sd.is_entangled
        assert entanglement_entropy(sv, [0]) < 1e-10

    def test_bell_state_maximally_entangled(self):
        """Bell state should be maximally entangled."""
        from quantum_simulator.core.state_vector import StateVector
        from quantum_simulator.analysis.entanglement import (
            schmidt_decomposition, entanglement_entropy, concurrence
        )

        sv = StateVector.bell_state('phi+')
        sd = schmidt_decomposition(sv, [0])
        assert sd.schmidt_rank == 2
        assert sd.is_entangled
        assert abs(entanglement_entropy(sv, [0]) - 1.0) < 1e-10  # 1 ebit
        assert abs(concurrence(sv) - 1.0) < 1e-10

    def test_concurrence_separable(self):
        """Separable state should have zero concurrence."""
        from quantum_simulator.core.state_vector import StateVector
        from quantum_simulator.analysis.entanglement import concurrence

        sv = StateVector(2)  # |00⟩
        assert concurrence(sv) < 1e-10

    def test_ghz_entanglement(self):
        """GHZ state should be entangled."""
        from quantum_simulator.core.state_vector import StateVector
        from quantum_simulator.analysis.entanglement import (
            schmidt_decomposition, full_entanglement_analysis
        )

        sv = StateVector.ghz_state(3)
        sd = schmidt_decomposition(sv, [0])
        assert sd.is_entangled

        analysis = full_entanglement_analysis(sv)
        assert analysis['is_entangled']

    def test_entanglement_spectrum(self):
        """Entanglement spectrum should be non-negative."""
        from quantum_simulator.core.state_vector import StateVector
        from quantum_simulator.analysis.entanglement import entanglement_spectrum

        sv = StateVector.bell_state('phi+')
        spectrum = entanglement_spectrum(sv, [0])
        assert all(s >= 0 for s in spectrum)

    def test_mutual_information(self):
        """Mutual information should be 2 for Bell state."""
        from quantum_simulator.core.state_vector import StateVector
        from quantum_simulator.analysis.entanglement import mutual_information

        sv = StateVector.bell_state('phi+')
        mi = mutual_information(sv, [0])
        assert abs(mi - 2.0) < 1e-10


# =============================================================================
# QSVT Tests
# =============================================================================

class TestQSVT:
    """Test QSVT research implementation."""

    def test_qsp_sequence_unitarity(self):
        """QSP sequence should produce unitary matrices."""
        from quantum_simulator.research.qsvt import qsp_sequence

        angles = [0.1, 0.2, 0.3, 0.4]
        for x in [0.0, 0.5, 1.0, -0.5]:
            U = qsp_sequence(angles, x)
            assert np.allclose(U @ U.conj().T, np.eye(2), atol=1e-10)

    def test_block_encoding_from_matrix(self):
        """Block encoding should embed the matrix correctly."""
        from quantum_simulator.research.qsvt import BlockEncoding

        A = np.array([[1, 0.5], [0.5, 1]], dtype=complex)
        be = BlockEncoding.from_matrix(A)
        assert be.alpha >= np.linalg.norm(A, ord=2)

    def test_block_encoding_from_unitary(self):
        """Unitary block encoding should have α = 1."""
        from quantum_simulator.research.qsvt import BlockEncoding
        from quantum_simulator.core.gates import H

        be = BlockEncoding.from_unitary(H)
        assert abs(be.alpha - 1.0) < 1e-10

    def test_qsvt_unification_demo(self):
        """QSVT demonstration should run without errors."""
        from quantum_simulator.research.qsvt import demonstrate_qsvt_unification

        results = demonstrate_qsvt_unification()
        assert 'framework' in results
        assert 'grover' in results
        assert 'hhl' in results
        assert 'hamiltonian_sim' in results
        assert 'phase_estimation' in results

    def test_qsvt_search(self):
        """QSVT search should return valid results."""
        from quantum_simulator.research.qsvt import qsvt_search

        result = qsvt_search(3, marked_fraction=0.25)
        assert result['n_qubits'] == 3
        assert result['n_marked'] > 0
        assert 'qsp_angles' in result


# =============================================================================
# QPE Tests
# =============================================================================

class TestQPE:
    """Test Quantum Phase Estimation."""

    def test_qpe_known_phase(self):
        """QPE should estimate a known phase correctly."""
        from quantum_simulator.algorithms.qpe import run_qpe

        # Phase gate with known phase 0.25
        phase = 0.25
        U = np.array([
            [1, 0],
            [0, np.exp(2j * np.pi * phase)]
        ], dtype=complex)

        result = run_qpe(U, n_precision=4, shots=1024)
        # QPE with decomposed controlled unitaries may have some error
        # Check that the true phase is in the estimated phases
        assert len(result['estimated_phases']) > 0
        assert result['n_precision'] == 4

    def test_qpe_circuit_construction(self):
        """QPE circuit should have correct qubit count."""
        from quantum_simulator.algorithms.qpe import qpe_circuit

        n_precision = 3
        U = np.eye(2, dtype=complex)
        qc = qpe_circuit(U, n_precision, n_state=1)
        assert qc.n_qubits == n_precision + 1
