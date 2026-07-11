"""
Quantum Approximate Optimization Algorithm (QAOA).

Reference: Farhi, Goldstone, Gutmann, arXiv:1411.4028 (2014)
"""

import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from scipy.optimize import minimize

from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import run_circuit, get_statevector


@dataclass
class QAOAProblem:
    """Combinatorial optimization problem encoded for QAOA."""
    n_qubits: int
    cost_terms: List[Tuple[float, List[int]]]  # (weight, qubit_indices) for ZZ terms
    linear_terms: List[Tuple[float, int]] = field(default_factory=list)  # (weight, qubit) for Z terms
    problem_name: str = ""

    def evaluate_cost(self, bitstring: str) -> float:
        """Evaluate cost function on a bitstring."""
        bits = [int(b) for b in bitstring]
        cost = 0.0

        for weight, qubits in self.cost_terms:
            if len(qubits) == 2:
                i, j = qubits
                s_i = 1 - 2 * bits[i]
                s_j = 1 - 2 * bits[j]
                cost += weight * s_i * s_j

        for weight, qubit in self.linear_terms:
            s = 1 - 2 * bits[qubit]
            cost += weight * s

        return cost

    def max_cost(self) -> Tuple[str, float]:
        """Find maximum cost by brute force (for small problems)."""
        best_cost = float('-inf')
        best_bitstring = ''
        for i in range(2 ** self.n_qubits):
            bs = format(i, f'0{self.n_qubits}b')
            c = self.evaluate_cost(bs)
            if c > best_cost:
                best_cost = c
                best_bitstring = bs
        return best_bitstring, best_cost

    @classmethod
    def max_cut(cls, n_vertices: int, edges: List[Tuple[int, int]], weights: Optional[List[float]] = None) -> 'QAOAProblem':
        """MaxCut problem: partition graph vertices to maximize cut edges."""
        if weights is None:
            weights = [1.0] * len(edges)

        cost_terms = []
        for (i, j), w in zip(edges, weights):
            cost_terms.append((w / 2, [i, j]))

        return cls(
            n_qubits=n_vertices,
            cost_terms=cost_terms,
            problem_name=f"MaxCut({n_vertices} vertices, {len(edges)} edges)"
        )

    @classmethod
    def max_independent_set(cls, n_vertices: int, edges: List[Tuple[int, int]]) -> 'QAOAProblem':
        """Maximum Independent Set: find largest set of non-adjacent vertices."""
        linear_terms = [(1.0, i) for i in range(n_vertices)]

        penalty = 2.0 * n_vertices
        cost_terms = [(-penalty, [i, j]) for i, j in edges]

        return cls(
            n_qubits=n_vertices,
            cost_terms=cost_terms,
            linear_terms=linear_terms,
            problem_name=f"MaxIndependentSet({n_vertices} vertices)"
        )


def qaoa_circuit(
    problem: QAOAProblem,
    gammas: List[float],
    betas: List[float]
) -> QuantumCircuit:
    """Construct a QAOA circuit for given problem and parameters."""
    assert len(gammas) == len(betas), "gammas and betas must have same length"
    p = len(gammas)
    n = problem.n_qubits

    qc = QuantumCircuit(n, name=f"qaoa_p{p}")

    for q in range(n):
        qc.h(q)

    for layer in range(p):
        for weight, qubits in problem.cost_terms:
            if len(qubits) == 2:
                i, j = qubits
                qc.cx(i, j)
                qc.rz(2 * gammas[layer] * weight, j)
                qc.cx(i, j)

        for weight, qubit in problem.linear_terms:
            qc.rz(2 * gammas[layer] * weight, qubit)

        for q in range(n):
            qc.rx(2 * betas[layer], q)

    return qc


@dataclass
class QAOAResult:
    """Result of QAOA optimization."""
    best_bitstring: str
    best_cost: float
    optimal_gammas: List[float]
    optimal_betas: List[float]
    convergence_history: List[float]
    iterations: int
    exact_solution: Optional[str] = None
    exact_cost: Optional[float] = None
    approximation_ratio: Optional[float] = None
    p_layers: int = 1
    problem_name: str = ""


def run_qaoa(
    problem: QAOAProblem,
    p: int = 1,
    initial_gammas: Optional[List[float]] = None,
    initial_betas: Optional[List[float]] = None,
    optimizer: str = "COBYLA",
    max_iterations: int = 200,
    shots: int = 1024
) -> QAOAResult:
    """Run QAOA to solve a combinatorial optimization problem."""
    if initial_gammas is None:
        np.random.seed(42)
        initial_gammas = np.random.uniform(0, np.pi, p).tolist()
    if initial_betas is None:
        np.random.seed(43)
        initial_betas = np.random.uniform(0, np.pi / 2, p).tolist()

    convergence_history = []

    def cost_function(params):
        gammas = params[:p].tolist()
        betas = params[p:].tolist()

        qc = qaoa_circuit(problem, gammas, betas)
        sv = get_statevector(qc)
        probs = sv.probabilities

        expected_cost = 0.0
        for i in range(2 ** problem.n_qubits):
            bs = format(i, f'0{problem.n_qubits}b')
            expected_cost += probs[i] * problem.evaluate_cost(bs)

        convergence_history.append(-expected_cost)
        return -expected_cost

    x0 = np.array(initial_gammas + initial_betas)

    result = minimize(
        cost_function, x0,
        method=optimizer,
        options={'maxiter': max_iterations}
    )

    opt_gammas = result.x[:p].tolist()
    opt_betas = result.x[p:].tolist()

    qc = qaoa_circuit(problem, opt_gammas, opt_betas)
    qc.measure_all()
    exec_result = run_circuit(qc, shots=shots)

    best_bs = max(exec_result.counts, key=lambda bs: problem.evaluate_cost(bs))
    best_cost = problem.evaluate_cost(best_bs)

    exact_bs, exact_cost = problem.max_cost()
    approx_ratio = best_cost / exact_cost if exact_cost != 0 else 1.0

    return QAOAResult(
        best_bitstring=best_bs,
        best_cost=best_cost,
        optimal_gammas=opt_gammas,
        optimal_betas=opt_betas,
        convergence_history=[-c for c in convergence_history],
        iterations=len(convergence_history),
        exact_solution=exact_bs,
        exact_cost=exact_cost,
        approximation_ratio=approx_ratio,
        p_layers=p,
        problem_name=problem.problem_name,
    )


def run_maxcut_qaoa(
    n_vertices: int,
    edges: List[Tuple[int, int]],
    p: int = 2,
    **kwargs
) -> QAOAResult:
    """Run QAOA for MaxCut."""
    problem = QAOAProblem.max_cut(n_vertices, edges)
    return run_qaoa(problem, p=p, **kwargs)
