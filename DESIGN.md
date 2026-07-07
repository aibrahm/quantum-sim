# Quantum Circuit Simulator Design Notes

A from-scratch quantum circuit simulator built on NumPy and SciPy with no external quantum framework, exposed through a FastAPI backend and a React frontend. This document explains the architecture and the reasoning behind the main design decisions.

## Architecture

```
React / TypeScript frontend  <->  FastAPI backend  <->  NumPy simulation core
```

The frontend is a thin, typed client that renders backend-computed state. All physics lives in the Python core, so there is one source of truth.

| Layer | Location | Responsibility |
|---|---|---|
| Core | `backend/quantum_simulator/core/` | State-vector and density-matrix engines, gates, measurement, Kraus noise channels |
| Circuits | `backend/quantum_simulator/circuit/` | Fluent circuit builder, OpenQASM export, executor |
| Algorithms | `backend/quantum_simulator/algorithms/` | Grover, Deutsch-Jozsa, teleportation, QFT, QPE, VQE, QAOA, error correction |
| Analysis | `backend/quantum_simulator/analysis/` | Entanglement measures, circuit statistics |
| Research | `backend/quantum_simulator/research/` | Quantum singular value transformation |
| API | `backend/quantum_simulator/api/` | FastAPI endpoints and a WebSocket for step-by-step execution |
| Frontend | `frontend/src/` | React, Zustand, TanStack Query, Three.js Bloch sphere |

## Design decisions

### State-vector as the primary representation
The pure state is a dense complex vector of `2^n` amplitudes. It is exact, supports arbitrary gates, and exposes amplitudes and observables directly, which suits an educational and visualization tool. A density matrix (`core/density_matrix.py`) is used only when noise is present, because mixed states cannot be represented by a state vector. Tensor-network or stabilizer methods scale better but only for restricted circuit classes; state-vector is the general-purpose exact baseline.

### Gate application by tensor contraction
A gate is applied by reshaping the amplitude vector into an n-index tensor and contracting only the axes the gate acts on, rather than building a `2^n x 2^n` matrix and multiplying. This is `O(2^n)` per gate instead of `O(4^n)`. The difference is dramatic in practice: applying a layer of gates on 10 qubits dropped from roughly 19 seconds to a few milliseconds. The public `apply_gate` API is unchanged; the contraction is an implementation detail.

### Qubit-ordering convention
The core is little-endian: qubit `q` is bit `(i >> q) & 1`, and measurement strings are printed with qubit 0 on the right. `apply_gate(gate, qubits)` treats `qubits[0]` as the most-significant bit of the gate index, which matches the textbook controlled-gate matrices and the intuitive `[control, target]` argument order. This single convention is enforced in one place (the gate kernel) and is consistent across gate application, measurement, the executor, and the circuit builder. An earlier version papered over an inconsistency with a name-based qubit-reordering table in the circuit layer; that has been removed in favor of one correct convention.

### Immutable state with an in-place fast path
`apply_gate` returns a new `StateVector`, which makes snapshots for step-by-step execution trivial and removes aliasing bugs. An in-place variant exists for hot loops. Terminal measurements are sampled once from the final distribution rather than re-simulating the circuit per shot; only mid-circuit measurement with feed-forward needs per-run handling.

### Density matrices and Kraus channels for noise
Noise is modeled with Kraus operators (`core/channels.py`): depolarizing, amplitude and phase damping, and readout error. Kraus operators are the standard completely-positive trace-preserving representation, and mixed states require the density matrix, at the cost of squaring the memory.

### FastAPI backend
The backend is FastAPI on Uvicorn with Pydantic v2 models and a WebSocket endpoint for streaming step-by-step execution. The async ASGI model, automatic OpenAPI docs, and request validation fit the structured circuit payloads well.

### Frontend
State (probabilities, amplitudes, Bloch vectors) lives in a Zustand store fetched from the backend. The Bloch sphere is a real Three.js scene with orbit controls and an animated state arrow. The circuit builder uses native HTML5 drag-and-drop and renders the circuit as SVG. A step control drives the backend WebSocket to animate state evolution live.

## Testing

The backend suite covers the core engine, circuits, algorithms, and analysis, including entanglement and measurement. An autouse fixture seeds NumPy's RNG before each test so runs are deterministic. Run with `pytest` from `backend/`. The frontend builds with `npm run build`.

## Known limitations and future work
- Practical qubit count is roughly 14 with the tensor-contraction kernel; the hard cap is 20. Beyond that, state-vector simulation is fundamentally exponential.
- The frontend WebSocket step-through is wired and type-checks; it exercises the backend live rather than simulating in the browser.
- CORS is restricted to a local development allowlist and would need configuration for deployment.
