"""
Quantum Approximate Optimization Algorithm (QAOA) Implementation.

QAOA is a variational algorithm for combinatorial optimization problems.
It prepares a quantum state by alternating between:
- Problem Hamiltonian evolution: e^{-iγC} (encodes the cost function)
- Mixer Hamiltonian evolution: e^{-iβB} (explores the solution space)

The depth p (number of layers) controls the quality of approximation.
At p → ∞, QAOA converges to the exact optimal solution.

Reference:
  Farhi, Goldstone, Gutmann - "A Quantum Approximate Optimization Algorithm"
  arXiv:1411.4028 (2014)
"""

import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from scipy.optimize import minimize
from itertools import combinations

from ..circuit.circuit import QuantumCircuit
from ..circuit.executor import run_circuit, get_statevector, ExecutionResult
from ..core.state_vector import StateVector


# =============================================================================
# Problem Encoding
# =============================================================================

@dataclass
class QAOAProblem:
    """
    Combinatorial optimization problem encoded for QAOA.

    The cost function C(z) maps bitstrings z ∈ {0,1}^n to real values.
    QAOA maximizes C by preparing quantum states that concentrate
    probability on high-cost bitstrings.
    """
    n_qubits: int
    cost_terms: List[Tuple[float, List[int]]]  # (weight, qubit_indices) for ZZ terms
    linear_terms: List[Tuple[float, int]] = field(default_factory=list)  # (weight, qubit) for Z terms
    problem_name: str = ""

    def evaluate_cost(self, bitstring: str) -> float:
        """Evaluate cost function on a bitstring."""
        bits = [int(b) for b in bitstring]
        cost = 0.0

        # Quadratic terms: w_ij * z_i * z_j (using ±1 encoding: z = 1-2*bit)
        for weight, qubits in self.cost_terms:
            if len(qubits) == 2:
                i, j = qubits
                s_i = 1 - 2 * bits[i]
                s_j = 1 - 2 * bits[j]
                cost += weight * s_i * s_j

        # Linear terms: w_i * z_i
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
        """
        MaxCut problem: partition graph vertices to maximize cut edges.

        The MaxCut cost function is: C(z) = Σ_{(i,j)∈E} w_{ij}(1 - z_i z_j)/2

        Args:
            n_vertices: Number of graph vertices
            edges: List of (i, j) edges
            weights: Edge weights (uniform if None)

        Returns:
            QAOAProblem encoding MaxCut
        """
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
        """
        Maximum Independent Set: find largest set of non-adjacent vertices.

        Args:
            n_vertices: Number of vertices
            edges: Graph edges

        Returns:
            QAOAProblem for MIS
        """
        # Linear terms: reward selecting each vertex
        linear_terms = [(1.0, i) for i in range(n_vertices)]

        # Penalty for selecting adjacent vertices
        penalty = 2.0 * n_vertices
        cost_terms = [(-penalty, [i, j]) for i, j in edges]

        return cls(
            n_qubits=n_vertices,
            cost_terms=cost_terms,
            linear_terms=linear_terms,
            problem_name=f"MaxIndependentSet({n_vertices} vertices)"
        )


# =============================================================================
# QAOA Circuit Construction
# =============================================================================

def qaoa_circuit(
    problem: QAOAProblem,
    gammas: List[float],
    betas: List[float]
) -> QuantumCircuit:
    """
    Construct a QAOA circuit for a given problem and parameters.

    Circuit structure:
    1. Initial state: |+⟩^⊗n (uniform superposition)
    2. For each layer p:
       a. Problem unitary: e^{-iγ_p C} (ZZ and Z rotations)
       b. Mixer unitary: e^{-iβ_p B} (X rotations)

    Args:
        problem: QAOA problem instance
        gammas: Problem layer parameters [γ₁, ..., γ_p]
        betas: Mixer layer parameters [β₁, ..., β_p]

    Returns:
        QAOA circuit
    """
    assert len(gammas) == len(betas), "gammas and betas must have same length"
    p = len(gammas)
    n = problem.n_qubits

    qc = QuantumCircuit(n, name=f"qaoa_p{p}")

    # Initial superposition |+⟩^⊗n
    for q in range(n):
        qc.h(q)

    # QAOA layers
    for layer in range(p):
        # Problem unitary: e^{-iγC}
        # ZZ terms: e^{-iγ·w·Z_i·Z_j} = CNOT(i,j) · Rz(2γw, j) · CNOT(i,j)
        for weight, qubits in problem.cost_terms:
            if len(qubits) == 2:
                i, j = qubits
                qc.cx(i, j)
                qc.rz(2 * gammas[layer] * weight, j)
                qc.cx(i, j)

        # Z terms: e^{-iγ·w·Z_i} = Rz(2γw, i)
        for weight, qubit in problem.linear_terms:
            qc.rz(2 * gammas[layer] * weight, qubit)

        # Mixer unitary: e^{-iβB} where B = Σ X_i
        # e^{-iβX} = Rx(2β)
        for q in range(n):
            qc.rx(2 * betas[layer], q)

    return qc


# =============================================================================
# QAOA Execution
# =============================================================================

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
    """
    Run QAOA to solve a combinatorial optimization problem.

    Args:
        problem: QAOA problem instance
        p: Number of QAOA layers (higher = better approximation)
        initial_gammas: Initial problem parameters
        initial_betas: Initial mixer parameters
        optimizer: Scipy optimizer name
        max_iterations: Max iterations for classical optimizer
        shots: Measurement shots per evaluation

    Returns:
        QAOAResult with optimal solution and parameters
    """
    if initial_gammas is None:
        np.random.seed(42)
        initial_gammas = np.random.uniform(0, np.pi, p).tolist()
    if initial_betas is None:
        np.random.seed(43)
        initial_betas = np.random.uniform(0, np.pi / 2, p).tolist()

    convergence_history = []

    def cost_function(params):
        """QAOA cost function: build circuit, sample, evaluate."""
        gammas = params[:p].tolist()
        betas = params[p:].tolist()

        qc = qaoa_circuit(problem, gammas, betas)
        sv = get_statevector(qc)
        probs = sv.probabilities

        # Compute expected cost
        expected_cost = 0.0
        for i in range(2 ** problem.n_qubits):
            bs = format(i, f'0{problem.n_qubits}b')
            expected_cost += probs[i] * problem.evaluate_cost(bs)

        convergence_history.append(-expected_cost)  # We minimize negative cost
        return -expected_cost  # Minimize = maximize cost

    # Initial parameters
    x0 = np.array(initial_gammas + initial_betas)

    # Optimize
    result = minimize(
        cost_function, x0,
        method=optimizer,
        options={'maxiter': max_iterations}
    )

    # Extract optimal parameters
    opt_gammas = result.x[:p].tolist()
    opt_betas = result.x[p:].tolist()

    # Run final circuit with optimal parameters and sample
    qc = qaoa_circuit(problem, opt_gammas, opt_betas)
    qc.measure_all()
    exec_result = run_circuit(qc, shots=shots)

    # Find best sampled bitstring
    best_bs = max(exec_result.counts, key=lambda bs: problem.evaluate_cost(bs))
    best_cost = problem.evaluate_cost(best_bs)

    # Exact solution for comparison
    exact_bs, exact_cost = problem.max_cost()
    approx_ratio = best_cost / exact_cost if exact_cost != 0 else 1.0

    return QAOAResult(
        best_bitstring=best_bs,
        best_cost=best_cost,
        optimal_gammas=opt_gammas,
        optimal_betas=opt_betas,
        convergence_history=[-c for c in convergence_history],  # Convert back to positive
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
    """
    Convenience function: Run QAOA for a MaxCut problem.

    Args:
        n_vertices: Number of graph vertices
        edges: Graph edges
        p: QAOA depth
        **kwargs: Additional arguments passed to run_qaoa

    Returns:
        QAOAResult for MaxCut
    """
    problem = QAOAProblem.max_cut(n_vertices, edges)
    return run_qaoa(problem, p=p, **kwargs)


# Export
__all__ = [
    'QAOAProblem',
    'QAOAResult',
    'qaoa_circuit',
    'run_qaoa',
    'run_maxcut_qaoa',
]
