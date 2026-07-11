"""Tests for QuantumCircuit and Executor."""

import numpy as np
import pytest
from quantum_simulator.circuit.circuit import QuantumCircuit, GateOperation, OperationType
from quantum_simulator.circuit.executor import (
    Executor, ExecutionResult, run_circuit, get_statevector
)
from quantum_simulator.core.state_vector import StateVector
from quantum_simulator.core.channels import NoiseModel, depolarizing_channel


class TestQuantumCircuitConstruction:
    """Test circuit construction."""

    def test_create_circuit(self):
        """Should create circuit with specified qubits."""
        qc = QuantumCircuit(3)
        assert qc.n_qubits == 3
        assert qc.n_classical == 3
        assert len(qc) == 0

    def test_add_single_qubit_gates(self):
        """Should add single-qubit gates."""
        qc = QuantumCircuit(2)
        qc.h(0).x(1).z(0)
        assert len(qc) == 3

    def test_add_two_qubit_gates(self):
        """Should add two-qubit gates."""
        qc = QuantumCircuit(2)
        qc.cx(0, 1).cz(1, 0)
        assert len(qc) == 2

    def test_add_rotation_gates(self):
        """Should add parameterized gates."""
        qc = QuantumCircuit(1)
        qc.rx(np.pi/2, 0).ry(np.pi, 0).rz(np.pi/4, 0)
        assert len(qc) == 3

    def test_fluent_interface(self):
        """Methods should return self for chaining."""
        qc = QuantumCircuit(2)
        result = qc.h(0).cx(0, 1).measure_all()
        assert result is qc

    def test_invalid_qubit_raises(self):
        """Should raise error for invalid qubit index."""
        qc = QuantumCircuit(2)
        with pytest.raises(ValueError):
            qc.h(5)

    def test_measurement(self):
        """Should add measurement operations."""
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1).measure(0, 0).measure(1, 1)
        ops = [op for op in qc.operations if op.op_type == OperationType.MEASUREMENT]
        assert len(ops) == 2


class TestQuantumCircuitSerialization:
    """Test circuit serialization."""

    def test_to_json_from_json(self):
        """Circuit should survive JSON round-trip."""
        qc = QuantumCircuit(2, name="test")
        qc.h(0).cx(0, 1).rx(np.pi/4, 0).measure_all()

        json_str = qc.to_json()
        qc_restored = QuantumCircuit.from_json(json_str)

        assert qc_restored.n_qubits == 2
        assert qc_restored.name == "test"
        assert len(qc_restored) == len(qc)

    def test_to_openqasm(self):
        """Should export to OpenQASM format."""
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1).measure_all()

        qasm = qc.to_openqasm()
        assert "OPENQASM 2.0" in qasm
        assert "qreg q[2]" in qasm
        assert "h q[0]" in qasm
        assert "cx q[0],q[1]" in qasm
        assert "measure q[0] -> c[0]" in qasm


class TestCircuitComposition:
    """Test circuit composition."""

    def test_compose(self):
        """compose should append circuits."""
        qc1 = QuantumCircuit(2)
        qc1.h(0)

        qc2 = QuantumCircuit(2)
        qc2.cx(0, 1)

        qc1.compose(qc2)
        assert len(qc1) == 2

    def test_inverse(self):
        """inverse should reverse gate order."""
        qc = QuantumCircuit(1)
        qc.h(0).t(0).s(0)

        inv = qc.inverse()
        ops = inv.gate_operations
        assert ops[0].gate_name == 'Sdg'
        assert ops[1].gate_name == 'Tdg'
        assert ops[2].gate_name == 'H'


class TestExecutor:
    """Test circuit execution."""

    def test_execute_simple_circuit(self):
        """Should execute simple circuit correctly."""
        qc = QuantumCircuit(1)
        qc.x(0).measure_all()

        result = run_circuit(qc, shots=100)
        # Should always measure |1⟩
        assert result.counts.get('1', 0) == 100

    def test_execute_bell_state(self):
        """Should create and measure Bell state correctly."""
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1).measure_all()

        result = run_circuit(qc, shots=1000)
        # Should only see |00⟩ and |11⟩
        assert set(result.counts.keys()).issubset({'00', '11'})
        # Each should be roughly 50%
        assert 400 < result.counts.get('00', 0) < 600
        assert 400 < result.counts.get('11', 0) < 600

    def test_get_statevector(self):
        """get_statevector should return final state."""
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1)

        sv = get_statevector(qc)
        # Bell state
        expected = np.array([1, 0, 0, 1]) / np.sqrt(2)
        assert np.allclose(sv.amplitudes, expected)

    def test_step_by_step_execution(self):
        """Should support step-by-step execution."""
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1)

        executor = Executor(qc, record_snapshots=True)

        snap1 = executor.step()
        assert snap1.operation_name == 'H'
        # After H on q0 (little-endian, q0 is the LSB): (|00⟩ + |01⟩)/√2
        assert np.isclose(snap1.probabilities[0], 0.5)
        assert np.isclose(snap1.probabilities[1], 0.5)

        snap2 = executor.step()
        assert snap2.operation_name == 'CX'
        # Bell state
        assert np.isclose(snap2.probabilities[0], 0.5)
        assert np.isclose(snap2.probabilities[3], 0.5)

    def test_execute_with_noise(self):
        """Should apply noise during execution."""
        qc = QuantumCircuit(1)
        qc.h(0)

        # Strong depolarizing noise
        noise = NoiseModel()
        noise.add_depolarizing(0.5)

        result = run_circuit(qc, shots=1000, noise_model=noise)
        # With noise, purity should be lower (closer to 50/50 even for |0⟩)
        # This is a weak test, mainly checking it doesn't crash


class TestSpecificCircuits:
    """Test specific quantum circuits."""

    def test_ghz_circuit(self):
        """Should create GHZ state."""
        qc = QuantumCircuit(3)
        qc.h(0).cx(0, 1).cx(1, 2)

        sv = get_statevector(qc)
        # GHZ: (|000⟩ + |111⟩)/√2
        assert np.isclose(np.abs(sv.amplitudes[0]), 1/np.sqrt(2))
        assert np.isclose(np.abs(sv.amplitudes[7]), 1/np.sqrt(2))

    def test_swap_test_circuit(self):
        """SWAP test should give fidelity estimate."""
        # For identical states, ancilla should measure 0
        qc = QuantumCircuit(3)
        # Prepare identical states on q1, q2
        qc.h(1).h(2)
        # SWAP test
        qc.h(0)
        qc.cswap(0, 1, 2)
        qc.h(0)

        result = run_circuit(qc, shots=1000)
        # P(0) = (1 + |⟨ψ|φ⟩|²)/2 = 1 for identical states
        # In this encoding, we measure q0
        zero_count = sum(v for k, v in result.counts.items() if k[2] == '0')
        assert zero_count > 900  # Should be close to 100%

    def test_superdense_coding(self):
        """Superdense coding should transmit 2 classical bits."""
        for msg in ['00', '01', '10', '11']:
            qc = QuantumCircuit(2)
            # Create Bell pair
            qc.h(0).cx(0, 1)

            # Alice encodes message on her qubit (q0)
            if msg[1] == '1':
                qc.x(0)
            if msg[0] == '1':
                qc.z(0)

            # Bob decodes
            qc.cx(0, 1).h(0).measure_all()

            result = run_circuit(qc, shots=100)
            # Deterministic recovery. Alice's Z bit (msg[0]) lands on q0 and her
            # X bit (msg[1]) on q1; counts strings are little-endian (q0 rightmost),
            # so the recovered key is msg reversed.
            assert result.counts.get(msg[::-1], 0) == 100


class TestExecutionResult:
    """Test ExecutionResult class."""

    def test_get_probabilities(self):
        """get_probabilities should convert counts."""
        result = ExecutionResult(
            counts={'00': 500, '11': 500},
            shots=1000
        )
        probs = result.get_probabilities()
        assert probs['00'] == 0.5
        assert probs['11'] == 0.5

    def test_to_dict(self):
        """Should serialize to dictionary."""
        result = ExecutionResult(
            counts={'0': 100},
            shots=100,
            execution_time_ms=5.0
        )
        data = result.to_dict()
        assert data['counts'] == {'0': 100}
        assert data['shots'] == 100


class TestBasisMeasurement:
    """Test measurement in X, Y, and Z bases."""

    def test_plus_state_x_basis_deterministic(self):
        """Measuring |+> in the X basis yields 0 with probability 1."""
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.measure(0, 0, basis='X')

        result = run_circuit(qc, shots=500)
        assert result.counts == {'0': 500}

    def test_minus_state_x_basis_deterministic(self):
        """Measuring |-> in the X basis yields 1 with probability 1."""
        qc = QuantumCircuit(1)
        qc.x(0)
        qc.h(0)
        qc.measure(0, 0, basis='X')

        result = run_circuit(qc, shots=500)
        assert result.counts == {'1': 500}

    def test_plus_i_state_y_basis_deterministic(self):
        """Measuring (|0>+i|1>)/sqrt(2) in the Y basis yields 0 with probability 1."""
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.s(0)
        qc.measure(0, 0, basis='Y')

        result = run_circuit(qc, shots=500)
        assert result.counts == {'0': 500}

    def test_zero_state_x_basis_uniform(self):
        """Measuring |0> in the X basis yields 0 and 1 with equal probability."""
        qc = QuantumCircuit(1)
        qc.measure(0, 0, basis='X')

        result = run_circuit(qc, shots=2000)
        assert abs(result.counts.get('0', 0) / 2000 - 0.5) < 0.1

    def test_mid_circuit_x_basis_post_state(self):
        """An X basis measurement must collapse to an X eigenstate, not a Z one."""
        # |+> measured in X gives outcome 0 and leaves |+>; H then maps it to |0>.
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.measure(0, 0, basis='X')
        qc.h(0)
        qc.measure(0, 0)

        result = run_circuit(qc, shots=200)
        assert result.counts == {'0': 200}

