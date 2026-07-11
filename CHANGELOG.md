# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-04

### Added

#### Research Implementation
- **QSVT (Quantum Singular Value Transformation)**: implementation of Gilyén, Su, Low, Wiebe (STOC 2019, arXiv:1806.01838), demonstrating how Grover's search, QPE, HHL matrix inversion, and Hamiltonian simulation are unified as polynomial transformations on singular values
- QSP angle finding via numerical optimization
- Block encoding construction for arbitrary matrices
- Demonstration mode showing all four unified algorithms

#### New Algorithms
- **Quantum Phase Estimation (QPE)**: full implementation with controlled-U^{2^k}, inverse QFT, and Hamiltonian eigenvalue estimation
- **Variational Quantum Eigensolver (VQE)**: H₂ molecular ground state, transverse Ising model, UCCSD and hardware-efficient ansätze, classical optimizer loop
- **QAOA**: Quantum Approximate Optimization for MaxCut and Max Independent Set with parameterized circuit layers
- **Quantum Error Correction**: 3-qubit bit-flip code, 3-qubit phase-flip code, Shor's 9-qubit code with syndrome measurement and correction

#### Circuit Optimization
- Multi-pass compiler-style optimizer with 5 passes: gate cancellation, single-qubit fusion (ZYZ decomposition), commutation analysis, CNOT optimization, rotation merging

#### Entanglement Analysis
- Schmidt decomposition with rank and entanglement fraction
- Von Neumann entropy and entanglement entropy
- Concurrence for pure and mixed states (Wootters' formula)
- Negativity via partial transpose
- Quantum mutual information
- Entanglement spectrum
- Pairwise entanglement heatmap

#### Frontend
- QSVT research panel with paper citations and interactive unification demo
- Algorithm panels for QPE, VQE, QAOA, QEC with full parameter controls
- Circuit optimizer tool with before/after comparison
- Entanglement analysis tool with Schmidt coefficients and heatmap visualization
- Light mode UI redesign with colored gate rendering

#### Infrastructure
- GitHub Actions CI/CD pipeline (Python 3.10–3.12 matrix, TypeScript checks, linting)
- Terraform IaC for AWS free-tier deployment (EC2 + S3)
- Automated deploy script

### Changed
- Expanded algorithm tabs from 4 to 8
- Header tabs now include VIS, ALGO, QSVT, TOOLS
- Renamed title to "Quantum Circuit Simulator"

## [1.0.0] - 2026-04-01

### Added
- State-vector simulation engine (up to 20 qubits) built from scratch with NumPy
- Density matrix simulation (up to 14 qubits) with noise channels
- 50+ quantum gates including parametric and multi-qubit gates
- Quantum algorithms: Grover's search, Deutsch-Jozsa, QFT, quantum teleportation
- Noise models: depolarizing, amplitude damping, phase damping channels
- FastAPI REST backend with WebSocket support for step-by-step execution
- React/TypeScript frontend with drag-and-drop circuit builder
- 3D Bloch sphere visualization (Three.js / React Three Fiber)
- Measurement histogram and state vector displays
- OpenQASM 2.0/3.0 export
- Redis persistence with in-memory fallback
- Docker and docker-compose configuration
- Comprehensive test suite (100+ unit tests)
