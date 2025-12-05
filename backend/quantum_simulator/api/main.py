"""
FastAPI application for Quantum Circuit Simulator.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import json

from .models import (
    CircuitCreateRequest, CircuitUpdateRequest, CircuitResponse,
    ExecutionRequest, ExecutionResultModel, StateVectorResponse,
    DensityMatrixResponse, CircuitStatsResponse, BlochVector,
    StateSnapshotModel, ErrorResponse, OpenQASMExport,
    GroverRequest, GroverResponse, VQERequest, VQEResponse,
    QFTRequest, QFTResponse, TeleportationRequest, TeleportationResponse,
    DeutschJozsaRequest, DeutschJozsaResponse,
)
from ..storage.redis_store import get_store, close_store, CircuitStore
from ..circuit.circuit import QuantumCircuit, OperationType
from ..circuit.executor import Executor, run_circuit, get_statevector, get_density_matrix
from ..core.channels import NoiseModel, depolarizing_channel, amplitude_damping, phase_damping
from ..analysis.circuit_stats import circuit_depth, gate_count, two_qubit_gate_count
from ..algorithms import (
    run_grover, optimal_iterations,
    run_deutsch_jozsa,
    qft_circuit, inverse_qft_circuit,
    run_teleportation,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await get_store()
    yield
    # Shutdown
    await close_store()


app = FastAPI(
    title="Quantum Circuit Simulator",
    description="A production-quality quantum circuit simulator API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# =============================================================================
# Circuit Management
# =============================================================================

@app.post("/api/circuit", response_model=CircuitResponse)
async def create_circuit(request: CircuitCreateRequest):
    """Create a new quantum circuit."""
    store = await get_store()

    # Create circuit
    n_classical = request.n_classical if request.n_classical else request.n_qubits
    qc = QuantumCircuit(request.n_qubits, n_classical, request.name)

    # Add operations
    for op in request.operations:
        if op.type == "gate" and op.gate:
            qc._add_gate(
                op.gate.gate_name,
                op.gate.qubits,
                op.gate.params,
                [],
                op.gate.label
            )
        elif op.type == "measurement" and op.measurement:
            for q, c in zip(op.measurement.qubits, op.measurement.classical_bits):
                qc.measure(q, c, op.measurement.basis)
        elif op.type == "barrier":
            qc.barrier(*op.qubits)
        elif op.type == "reset":
            for q in op.qubits:
                qc.reset(q)

    # Generate ID and save
    circuit_id = await store.generate_id()
    await store.save_circuit(circuit_id, qc)

    # Build response
    return _build_circuit_response(circuit_id, qc)


@app.get("/api/circuit/{circuit_id}", response_model=CircuitResponse)
async def get_circuit(circuit_id: str):
    """Get circuit by ID."""
    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        raise HTTPException(status_code=404, detail="Circuit not found")

    return _build_circuit_response(circuit_id, qc)


@app.put("/api/circuit/{circuit_id}", response_model=CircuitResponse)
async def update_circuit(circuit_id: str, request: CircuitUpdateRequest):
    """Update circuit operations."""
    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        raise HTTPException(status_code=404, detail="Circuit not found")

    # Clear existing operations
    qc._operations = []

    # Add new operations
    for op in request.operations:
        if op.type == "gate" and op.gate:
            qc._add_gate(
                op.gate.gate_name,
                op.gate.qubits,
                op.gate.params,
                [],
                op.gate.label
            )
        elif op.type == "measurement" and op.measurement:
            for q, c in zip(op.measurement.qubits, op.measurement.classical_bits):
                qc.measure(q, c, op.measurement.basis)
        elif op.type == "barrier":
            qc.barrier(*op.qubits)
        elif op.type == "reset":
            for q in op.qubits:
                qc.reset(q)

    await store.save_circuit(circuit_id, qc)
    return _build_circuit_response(circuit_id, qc)


@app.delete("/api/circuit/{circuit_id}")
async def delete_circuit(circuit_id: str):
    """Delete a circuit."""
    store = await get_store()
    deleted = await store.delete_circuit(circuit_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Circuit not found")

    return {"status": "deleted", "circuit_id": circuit_id}


# =============================================================================
# Execution
# =============================================================================

@app.post("/api/circuit/{circuit_id}/run", response_model=ExecutionResultModel)
async def run_circuit_endpoint(circuit_id: str, request: ExecutionRequest):
    """Execute a circuit."""
    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        raise HTTPException(status_code=404, detail="Circuit not found")

    # Build noise model if specified
    noise_model = None
    if request.noise:
        noise_model = NoiseModel()
        if request.noise.depolarizing_rate:
            noise_model.add_depolarizing(request.noise.depolarizing_rate)
        if request.noise.amplitude_damping:
            noise_model.add_amplitude_damping(request.noise.amplitude_damping)
        if request.noise.phase_damping:
            noise_model.add_phase_damping(request.noise.phase_damping)
        if request.noise.readout_error:
            for qubit, errors in request.noise.readout_error.items():
                noise_model.add_readout_error(int(qubit), errors[0], errors[1])

    # Execute
    result = run_circuit(
        qc,
        shots=request.shots,
        mode=request.mode.value,
        noise_model=noise_model,
        record_snapshots=request.record_snapshots
    )

    # Build response
    snapshots = []
    if request.record_snapshots:
        for snap in result.snapshots:
            bloch_vecs = [
                BlochVector(qubit=i, x=b[0], y=b[1], z=b[2])
                for i, b in enumerate(snap.bloch_vectors)
            ]
            snapshots.append(StateSnapshotModel(
                step=snap.step,
                operation_type=snap.operation_type,
                operation_name=snap.operation_name,
                qubits=snap.qubits,
                params=snap.params,
                probabilities=snap.probabilities.tolist(),
                bloch_vectors=bloch_vecs,
                measurement_outcome=snap.measurement_outcome
            ))

    return ExecutionResultModel(
        circuit_id=circuit_id,
        counts=result.counts,
        shots=result.shots,
        probabilities=result.get_probabilities(),
        execution_time_ms=result.execution_time_ms,
        snapshots=snapshots
    )


@app.get("/api/circuit/{circuit_id}/state", response_model=StateVectorResponse)
async def get_circuit_state(circuit_id: str):
    """Get state vector of circuit (no measurements)."""
    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        raise HTTPException(status_code=404, detail="Circuit not found")

    # Remove measurements for state vector calculation
    qc_copy = QuantumCircuit(qc.n_qubits, qc.n_classical, qc.name)
    for op in qc.operations:
        if op.op_type == OperationType.GATE:
            qc_copy._add_gate(
                op.operation.gate_name,
                op.operation.qubits,
                op.operation.params
            )

    sv = get_statevector(qc_copy)

    bloch_vecs = [
        BlochVector(qubit=i, x=b[0], y=b[1], z=b[2])
        for i, b in enumerate(sv.all_bloch_vectors())
    ]

    return StateVectorResponse(
        circuit_id=circuit_id,
        n_qubits=sv.n_qubits,
        amplitudes_real=sv.amplitudes.real.tolist(),
        amplitudes_imag=sv.amplitudes.imag.tolist(),
        probabilities=sv.probabilities.tolist(),
        bloch_vectors=bloch_vecs
    )


@app.get("/api/circuit/{circuit_id}/bloch")
async def get_bloch_vectors(circuit_id: str):
    """Get Bloch sphere data for all qubits."""
    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        raise HTTPException(status_code=404, detail="Circuit not found")

    # Get state vector
    qc_copy = QuantumCircuit(qc.n_qubits, qc.n_classical, qc.name)
    for op in qc.operations:
        if op.op_type == OperationType.GATE:
            qc_copy._add_gate(
                op.operation.gate_name,
                op.operation.qubits,
                op.operation.params
            )

    sv = get_statevector(qc_copy)
    bloch_vecs = sv.all_bloch_vectors()

    return {
        "circuit_id": circuit_id,
        "bloch_vectors": [
            {"qubit": i, "x": b[0], "y": b[1], "z": b[2]}
            for i, b in enumerate(bloch_vecs)
        ]
    }


@app.get("/api/circuit/{circuit_id}/probabilities")
async def get_probabilities(circuit_id: str):
    """Get probability distribution."""
    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        raise HTTPException(status_code=404, detail="Circuit not found")

    qc_copy = QuantumCircuit(qc.n_qubits, qc.n_classical, qc.name)
    for op in qc.operations:
        if op.op_type == OperationType.GATE:
            qc_copy._add_gate(
                op.operation.gate_name,
                op.operation.qubits,
                op.operation.params
            )

    sv = get_statevector(qc_copy)
    probs = sv.probabilities

    return {
        "circuit_id": circuit_id,
        "probabilities": {
            format(i, f'0{qc.n_qubits}b'): float(p)
            for i, p in enumerate(probs) if p > 1e-10
        }
    }


# =============================================================================
# Analysis
# =============================================================================

@app.get("/api/circuit/{circuit_id}/stats", response_model=CircuitStatsResponse)
async def get_circuit_stats(circuit_id: str):
    """Get circuit statistics."""
    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        raise HTTPException(status_code=404, detail="Circuit not found")

    gates = gate_count(qc)
    measurements = sum(
        1 for op in qc.operations if op.op_type == OperationType.MEASUREMENT
    )

    return CircuitStatsResponse(
        circuit_id=circuit_id,
        n_qubits=qc.n_qubits,
        depth=circuit_depth(qc),
        total_gates=sum(gates.values()),
        gate_counts=gates,
        two_qubit_gates=two_qubit_gate_count(qc),
        measurements=measurements
    )


# =============================================================================
# Export
# =============================================================================

@app.get("/api/circuit/{circuit_id}/openqasm", response_model=OpenQASMExport)
async def export_openqasm(circuit_id: str, version: str = "2.0"):
    """Export circuit to OpenQASM."""
    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        raise HTTPException(status_code=404, detail="Circuit not found")

    return OpenQASMExport(
        circuit_id=circuit_id,
        qasm=qc.to_openqasm(version),
        version=version
    )


# =============================================================================
# Algorithms
# =============================================================================

@app.post("/api/algorithms/grover", response_model=GroverResponse)
async def run_grover_algorithm(request: GroverRequest):
    """Run Grover's search algorithm."""
    try:
        n_qubits = request.n_qubits
        marked_states = request.marked_states
        iterations = request.iterations

        # Validate marked states
        max_state = 2 ** n_qubits - 1
        for state in marked_states:
            if state < 0 or state > max_state:
                raise HTTPException(
                    status_code=400,
                    detail=f"Marked state {state} out of range [0, {max_state}]"
                )

        # Run Grover's algorithm
        result, success_prob = run_grover(
            n_qubits=n_qubits,
            marked_states=marked_states,
            iterations=iterations,
            shots=1024
        )

        opt_iter = optimal_iterations(n_qubits, len(marked_states))
        used_iter = iterations if iterations else opt_iter

        return GroverResponse(
            counts=result.counts,
            shots=result.shots,
            iterations_used=used_iter,
            success_probability=success_prob,
            optimal_iterations=opt_iter
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/algorithms/deutsch-jozsa", response_model=DeutschJozsaResponse)
async def run_deutsch_jozsa_algorithm(request: DeutschJozsaRequest):
    """Run Deutsch-Jozsa algorithm."""
    try:
        result = run_deutsch_jozsa(
            n_qubits=request.n_qubits,
            oracle_type=request.oracle_type,
            shots=request.shots
        )

        return DeutschJozsaResponse(
            oracle_type=result["oracle_type"],
            detected_type=result["detected_type"],
            correct=result["correct"],
            counts=result["counts"],
            shots=result["shots"],
            zero_probability=result["zero_probability"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/algorithms/qft", response_model=QFTResponse)
async def run_qft_algorithm(request: QFTRequest):
    """Run Quantum Fourier Transform."""
    try:
        n_qubits = request.n_qubits
        input_state = request.input_state or [0] * n_qubits
        inverse = request.inverse

        # Build circuit
        qc = QuantumCircuit(n_qubits, name="qft_run")

        # Prepare input state (computational basis)
        for i, bit in enumerate(input_state):
            if bit == 1:
                qc.x(i)

        # Apply QFT or inverse QFT
        if inverse:
            iqft = inverse_qft_circuit(n_qubits)
            qc.compose(iqft)
        else:
            qft = qft_circuit(n_qubits)
            qc.compose(qft)

        # Measure
        qc.measure_all()

        # Run
        result = run_circuit(qc, shots=request.shots)

        return QFTResponse(
            n_qubits=n_qubits,
            input_state=input_state,
            inverse=inverse,
            counts=result.counts,
            probabilities=result.get_probabilities(),
            shots=result.shots
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/algorithms/teleportation", response_model=TeleportationResponse)
async def run_teleportation_algorithm(request: TeleportationRequest):
    """Run quantum teleportation demonstration."""
    try:
        result = run_teleportation(
            theta=request.state_theta,
            phi=request.state_phi,
            shots=request.shots
        )

        return TeleportationResponse(
            input_bloch=result["input_state"]["bloch"],
            output_bloch=result["output_state"]["bloch"],
            fidelity=result["fidelity"],
            counts=result["counts"],
            shots=result["shots"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WebSocket for Real-time Execution
# =============================================================================

@app.websocket("/ws/circuit/{circuit_id}/execute")
async def websocket_execute(websocket: WebSocket, circuit_id: str):
    """WebSocket for step-by-step execution with real-time updates."""
    await websocket.accept()

    store = await get_store()
    qc = await store.get_circuit(circuit_id)

    if qc is None:
        await websocket.send_json({"error": "Circuit not found"})
        await websocket.close()
        return

    try:
        executor = Executor(qc, record_snapshots=True)

        # Send initial state
        await websocket.send_json({
            "type": "init",
            "n_qubits": qc.n_qubits,
            "total_steps": len(qc)
        })

        while True:
            # Wait for command
            data = await websocket.receive_text()
            cmd = json.loads(data)

            if cmd.get("action") == "step":
                snapshot = executor.step()
                if snapshot:
                    bloch_vecs = [
                        {"qubit": i, "x": b[0], "y": b[1], "z": b[2]}
                        for i, b in enumerate(snapshot.bloch_vectors)
                    ]
                    await websocket.send_json({
                        "type": "step",
                        "step": snapshot.step,
                        "operation": snapshot.operation_name,
                        "qubits": snapshot.qubits,
                        "probabilities": snapshot.probabilities.tolist(),
                        "bloch_vectors": bloch_vecs
                    })
                else:
                    await websocket.send_json({
                        "type": "complete",
                        "message": "Execution complete"
                    })

            elif cmd.get("action") == "run_all":
                while True:
                    snapshot = executor.step()
                    if snapshot is None:
                        break
                    bloch_vecs = [
                        {"qubit": i, "x": b[0], "y": b[1], "z": b[2]}
                        for i, b in enumerate(snapshot.bloch_vectors)
                    ]
                    await websocket.send_json({
                        "type": "step",
                        "step": snapshot.step,
                        "operation": snapshot.operation_name,
                        "qubits": snapshot.qubits,
                        "probabilities": snapshot.probabilities.tolist(),
                        "bloch_vectors": bloch_vecs
                    })
                await websocket.send_json({
                    "type": "complete",
                    "message": "Execution complete"
                })

            elif cmd.get("action") == "reset":
                executor.reset()
                await websocket.send_json({
                    "type": "reset",
                    "message": "Executor reset"
                })

            elif cmd.get("action") == "close":
                break

    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()


# =============================================================================
# Helper Functions
# =============================================================================

def _build_circuit_response(circuit_id: str, qc: QuantumCircuit) -> CircuitResponse:
    """Build CircuitResponse from QuantumCircuit."""
    from .models import CircuitOperationModel, GateOperationModel, MeasurementModel

    operations = []
    for op in qc.operations:
        if op.op_type == OperationType.GATE:
            operations.append(CircuitOperationModel(
                type="gate",
                gate=GateOperationModel(
                    gate_name=op.operation.gate_name,
                    qubits=op.operation.qubits,
                    params=op.operation.params,
                    label=op.operation.label
                ),
                qubits=op.qubits
            ))
        elif op.op_type == OperationType.MEASUREMENT:
            operations.append(CircuitOperationModel(
                type="measurement",
                measurement=MeasurementModel(
                    qubits=op.operation.qubits,
                    classical_bits=op.operation.classical_bits,
                    basis=op.operation.basis
                ),
                qubits=op.qubits
            ))
        elif op.op_type == OperationType.BARRIER:
            operations.append(CircuitOperationModel(
                type="barrier",
                qubits=op.qubits
            ))
        elif op.op_type == OperationType.RESET:
            operations.append(CircuitOperationModel(
                type="reset",
                qubits=op.qubits
            ))

    return CircuitResponse(
        id=circuit_id,
        n_qubits=qc.n_qubits,
        n_classical=qc.n_classical,
        name=qc.name,
        operations=operations,
        depth=circuit_depth(qc),
        gate_count=gate_count(qc)
    )


# Run with: uvicorn quantum_simulator.api.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
