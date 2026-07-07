"""Cross-validation against Qiskit as an oracle.

Every gate and a battery of randomized circuits are executed on both this
simulator and Qiskit's Statevector backend; final states must agree up to
global phase (fidelity 1). Skipped automatically when qiskit is not installed.
"""

import numpy as np
import pytest

qiskit = pytest.importorskip("qiskit")

from qiskit import QuantumCircuit as QiskitCircuit
from qiskit.circuit.library import SwapGate, iSwapGate
from qiskit.quantum_info import Statevector

from quantum_simulator.core import gates
from quantum_simulator.core.state_vector import StateVector

TOL = 1e-9


def fidelity(a: np.ndarray, b: np.ndarray) -> float:
    return float(abs(np.vdot(a, b)) ** 2)


def random_prep(n: int, rng: np.random.Generator):
    """Identical generic state prep on both simulators: one Ry+Rz per qubit."""
    sv = StateVector(n)
    qc = QiskitCircuit(n)
    for q in range(n):
        theta, phi = rng.uniform(0, 2 * np.pi, size=2)
        sv = sv.apply_gate(gates.Ry(theta), [q]).apply_gate(gates.Rz(phi), [q])
        qc.ry(theta, q)
        qc.rz(phi, q)
    return sv, qc


def assert_match(sv: StateVector, qc: QiskitCircuit):
    ours = sv.amplitudes
    ref = np.asarray(Statevector.from_instruction(qc))
    assert fidelity(ours, ref) > 1 - TOL, (
        f"state mismatch: ours={np.round(ours, 4)} qiskit={np.round(ref, 4)}"
    )


# Gate name -> how to apply the same gate in Qiskit. `None` params = fixed gate.
SINGLE_QUBIT = {
    'I': lambda qc, q: qc.id(q),
    'X': lambda qc, q: qc.x(q),
    'Y': lambda qc, q: qc.y(q),
    'Z': lambda qc, q: qc.z(q),
    'H': lambda qc, q: qc.h(q),
    'S': lambda qc, q: qc.s(q),
    'Sdg': lambda qc, q: qc.sdg(q),
    'T': lambda qc, q: qc.t(q),
    'Tdg': lambda qc, q: qc.tdg(q),
    'SX': lambda qc, q: qc.sx(q),
    'SXdg': lambda qc, q: qc.sxdg(q),
}

PARAM_SINGLE = {
    'Rx': (1, lambda qc, p, q: qc.rx(p[0], q)),
    'Ry': (1, lambda qc, p, q: qc.ry(p[0], q)),
    'Rz': (1, lambda qc, p, q: qc.rz(p[0], q)),
    'Phase': (1, lambda qc, p, q: qc.p(p[0], q)),
    'U1': (1, lambda qc, p, q: qc.p(p[0], q)),
    'U2': (2, lambda qc, p, q: qc.u(np.pi / 2, p[0], p[1], q)),
    'U3': (3, lambda qc, p, q: qc.u(p[0], p[1], p[2], q)),
}

TWO_QUBIT = {
    'CNOT': lambda qc, a, b: qc.cx(a, b),
    'CX': lambda qc, a, b: qc.cx(a, b),
    'CY': lambda qc, a, b: qc.cy(a, b),
    'CZ': lambda qc, a, b: qc.cz(a, b),
    'SWAP': lambda qc, a, b: qc.swap(a, b),
    'iSWAP': lambda qc, a, b: qc.iswap(a, b),
    'SQSWAP': lambda qc, a, b: qc.append(SwapGate().power(0.5), [a, b]),
}

PARAM_TWO = {
    'CRx': (1, lambda qc, p, a, b: qc.crx(p[0], a, b)),
    'CRy': (1, lambda qc, p, a, b: qc.cry(p[0], a, b)),
    'CRz': (1, lambda qc, p, a, b: qc.crz(p[0], a, b)),
    'CPhase': (1, lambda qc, p, a, b: qc.cp(p[0], a, b)),
    'Rxx': (1, lambda qc, p, a, b: qc.rxx(p[0], a, b)),
    'Ryy': (1, lambda qc, p, a, b: qc.ryy(p[0], a, b)),
    'Rzz': (1, lambda qc, p, a, b: qc.rzz(p[0], a, b)),
}

THREE_QUBIT = {
    'TOFFOLI': lambda qc, a, b, c: qc.ccx(a, b, c),
    'FREDKIN': lambda qc, a, b, c: qc.cswap(a, b, c),
}


class TestEveryGateAgainstQiskit:
    """Each gate applied to a generic 3-qubit state, on every qubit placement."""

    @pytest.mark.parametrize("name", sorted(SINGLE_QUBIT))
    def test_single_qubit(self, name):
        rng = np.random.default_rng(7)
        for q in range(3):
            sv, qc = random_prep(3, rng)
            sv = sv.apply_gate(gates.get_gate(name), [q])
            SINGLE_QUBIT[name](qc, q)
            assert_match(sv, qc)

    @pytest.mark.parametrize("name", sorted(PARAM_SINGLE))
    def test_param_single_qubit(self, name):
        rng = np.random.default_rng(11)
        n_params, apply_ref = PARAM_SINGLE[name]
        for q in range(3):
            params = list(rng.uniform(0, 2 * np.pi, size=n_params))
            sv, qc = random_prep(3, rng)
            sv = sv.apply_gate(gates.get_gate(name, params), [q])
            apply_ref(qc, params, q)
            assert_match(sv, qc)

    @pytest.mark.parametrize("name", sorted(TWO_QUBIT))
    def test_two_qubit(self, name):
        rng = np.random.default_rng(13)
        for a in range(3):
            for b in range(3):
                if a == b:
                    continue
                sv, qc = random_prep(3, rng)
                sv = sv.apply_gate(gates.get_gate(name), [a, b])
                TWO_QUBIT[name](qc, a, b)
                assert_match(sv, qc)

    @pytest.mark.parametrize("name", sorted(PARAM_TWO))
    def test_param_two_qubit(self, name):
        rng = np.random.default_rng(17)
        n_params, apply_ref = PARAM_TWO[name]
        for a in range(3):
            for b in range(3):
                if a == b:
                    continue
                params = list(rng.uniform(0, 2 * np.pi, size=n_params))
                sv, qc = random_prep(3, rng)
                sv = sv.apply_gate(gates.get_gate(name, params), [a, b])
                apply_ref(qc, params, a, b)
                assert_match(sv, qc)

    @pytest.mark.parametrize("name", sorted(THREE_QUBIT))
    def test_three_qubit(self, name):
        rng = np.random.default_rng(19)
        from itertools import permutations
        for a, b, c in permutations(range(3)):
            sv, qc = random_prep(3, rng)
            sv = sv.apply_gate(gates.get_gate(name), [a, b, c])
            THREE_QUBIT[name](qc, a, b, c)
            assert_match(sv, qc)


# Pool for randomized circuits: (name, arity, n_params, qiskit applier)
FUZZ_POOL = (
    [(n, 1, 0, SINGLE_QUBIT[n]) for n in SINGLE_QUBIT]
    + [(n, 1, PARAM_SINGLE[n][0], PARAM_SINGLE[n][1]) for n in PARAM_SINGLE]
    + [(n, 2, 0, TWO_QUBIT[n]) for n in TWO_QUBIT]
    + [(n, 2, PARAM_TWO[n][0], PARAM_TWO[n][1]) for n in PARAM_TWO]
    + [(n, 3, 0, THREE_QUBIT[n]) for n in THREE_QUBIT]
)


class TestRandomCircuitsAgainstQiskit:
    """Randomized deep circuits over the full gate set, seeded and deterministic."""

    @pytest.mark.parametrize("seed", range(30))
    def test_random_circuit(self, seed):
        rng = np.random.default_rng(1000 + seed)
        n = int(rng.integers(2, 6))
        depth = 20
        sv, qc = random_prep(n, rng)

        for _ in range(depth):
            name, arity, n_params, apply_ref = FUZZ_POOL[int(rng.integers(len(FUZZ_POOL)))]
            if arity > n:
                continue
            qubits = list(rng.choice(n, size=arity, replace=False).astype(int))
            params = list(rng.uniform(0, 2 * np.pi, size=n_params)) if n_params else None
            sv = sv.apply_gate(gates.get_gate(name, params), qubits)
            if n_params:
                apply_ref(qc, params, *qubits)
            else:
                apply_ref(qc, *qubits)

        assert np.isclose(np.linalg.norm(sv.amplitudes), 1.0, atol=1e-10)
        assert_match(sv, qc)
