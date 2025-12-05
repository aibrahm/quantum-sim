"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union, Literal
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class SimulationMode(str, Enum):
    STATEVECTOR = "statevector"
    DENSITY_MATRIX = "density_matrix"


class GateName(str, Enum):
    # Single-qubit gates
    I = "I"
    X = "X"
    Y = "Y"
    Z = "Z"
    H = "H"
    S = "S"
    SDG = "Sdg"
    T = "T"
    TDG = "Tdg"
    SX = "SX"
    SXDG = "SXdg"
    # Rotation gates
    RX = "Rx"
    RY = "Ry"
    RZ = "Rz"
    PHASE = "Phase"
    U1 = "U1"
    U2 = "U2"
    U3 = "U3"
    # Two-qubit gates
    CX = "CX"
    CY = "CY"
    CZ = "CZ"
    SWAP = "SWAP"
    ISWAP = "iSWAP"
    CRX = "CRx"
    CRY = "CRy"
    CRZ = "CRz"
    CPHASE = "CPhase"
    RXX = "Rxx"
    RYY = "Ryy"
    RZZ = "Rzz"
    # Three-qubit gates
    CCX = "CCX"
    CSWAP = "CSWAP"


# =============================================================================
# Gate and Operation Models
# =============================================================================

class GateOperationModel(BaseModel):
    """Model for a gate operation."""
    gate_name: str
    qubits: List[int]
    params: List[float] = []
    label: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "gate_name": "H",
                "qubits": [0],
                "params": []
            }
        }


class MeasurementModel(BaseModel):
    """Model for a measurement operation."""
    qubits: List[int]
    classical_bits: List[int]
    basis: str = "Z"


class CircuitOperationModel(BaseModel):
    """Model for any circuit operation."""
    type: Literal["gate", "measurement", "barrier", "reset"]
    gate: Optional[GateOperationModel] = None
    measurement: Optional[MeasurementModel] = None
    qubits: List[int] = []


# =============================================================================
# Circuit Models
# =============================================================================

class CircuitCreateRequest(BaseModel):
    """Request to create a new circuit."""
    n_qubits: int = Field(..., ge=1, le=20, description="Number of qubits")
    n_classical: Optional[int] = Field(None, ge=0, description="Number of classical bits")
    name: str = "circuit"
    operations: List[CircuitOperationModel] = []

    class Config:
        json_schema_extra = {
            "example": {
                "n_qubits": 2,
                "name": "bell_state",
                "operations": [
                    {"type": "gate", "gate": {"gate_name": "H", "qubits": [0]}},
                    {"type": "gate", "gate": {"gate_name": "CX", "qubits": [0, 1]}},
                ]
            }
        }


class CircuitUpdateRequest(BaseModel):
    """Request to update circuit operations."""
    operations: List[CircuitOperationModel]


class CircuitResponse(BaseModel):
    """Response containing circuit details."""
    id: str
    n_qubits: int
    n_classical: int
    name: str
    operations: List[CircuitOperationModel]
    depth: int
    gate_count: Dict[str, int]


# =============================================================================
# Execution Models
# =============================================================================

class NoiseConfig(BaseModel):
    """Configuration for noise model."""
    depolarizing_rate: Optional[float] = Field(None, ge=0, le=1)
    amplitude_damping: Optional[float] = Field(None, ge=0, le=1)
    phase_damping: Optional[float] = Field(None, ge=0, le=1)
    readout_error: Optional[Dict[int, List[float]]] = None  # {qubit: [p01, p10]}


class ExecutionRequest(BaseModel):
    """Request to execute a circuit."""
    shots: int = Field(1024, ge=1, le=100000)
    mode: SimulationMode = SimulationMode.STATEVECTOR
    noise: Optional[NoiseConfig] = None
    record_snapshots: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "shots": 1024,
                "mode": "statevector",
                "record_snapshots": False
            }
        }


class StepRequest(BaseModel):
    """Request for step-by-step execution."""
    target_step: Optional[int] = None  # None means next step


# =============================================================================
# Result Models
# =============================================================================

class BlochVector(BaseModel):
    """Bloch sphere coordinates for a qubit."""
    qubit: int
    x: float
    y: float
    z: float


class StateSnapshotModel(BaseModel):
    """Snapshot of circuit state at a step."""
    step: int
    operation_type: str
    operation_name: str
    qubits: List[int]
    params: List[float]
    probabilities: List[float]
    bloch_vectors: List[BlochVector]
    measurement_outcome: Optional[int] = None


class ExecutionResultModel(BaseModel):
    """Result of circuit execution."""
    circuit_id: str
    counts: Dict[str, int]
    shots: int
    probabilities: Dict[str, float]
    execution_time_ms: float
    snapshots: List[StateSnapshotModel] = []


class StateVectorResponse(BaseModel):
    """Response containing state vector data."""
    circuit_id: str
    n_qubits: int
    amplitudes_real: List[float]
    amplitudes_imag: List[float]
    probabilities: List[float]
    bloch_vectors: List[BlochVector]


class DensityMatrixResponse(BaseModel):
    """Response containing density matrix data."""
    circuit_id: str
    n_qubits: int
    matrix_real: List[List[float]]
    matrix_imag: List[List[float]]
    purity: float
    entropy: float
    bloch_vectors: List[BlochVector]


# =============================================================================
# Analysis Models
# =============================================================================

class CircuitStatsResponse(BaseModel):
    """Circuit statistics."""
    circuit_id: str
    n_qubits: int
    depth: int
    total_gates: int
    gate_counts: Dict[str, int]
    two_qubit_gates: int
    measurements: int


class MetricsResponse(BaseModel):
    """Quantum state metrics."""
    circuit_id: str
    purity: float
    entropy: float
    fidelity_to_target: Optional[float] = None


class EntanglementResponse(BaseModel):
    """Entanglement analysis."""
    circuit_id: str
    entanglement_map: List[List[float]]  # Pairwise entanglement
    total_entanglement: float


# =============================================================================
# Algorithm Models
# =============================================================================

class GroverRequest(BaseModel):
    """Request to run Grover's algorithm."""
    n_qubits: int = Field(..., ge=2, le=10)
    marked_states: List[int]
    iterations: Optional[int] = None  # Auto-calculate if None


class GroverResponse(BaseModel):
    """Result of Grover's algorithm."""
    counts: Dict[str, int]
    shots: int
    iterations_used: int
    success_probability: float
    optimal_iterations: int


class VQERequest(BaseModel):
    """Request to run VQE."""
    hamiltonian_type: Literal["h2", "custom"]
    bond_length: Optional[float] = 0.735  # For H2
    custom_hamiltonian: Optional[List[Dict[str, Any]]] = None  # Pauli strings
    ansatz: str = "uccsd"
    max_iterations: int = 100
    initial_params: Optional[List[float]] = None


class VQEResponse(BaseModel):
    """Result of VQE."""
    ground_state_energy: float
    optimal_params: List[float]
    convergence_history: List[float]
    iterations: int


class QFTRequest(BaseModel):
    """Request to run QFT."""
    n_qubits: int = Field(..., ge=1, le=10)
    input_state: Optional[List[int]] = None  # Computational basis state
    inverse: bool = False
    shots: int = 1024


class QFTResponse(BaseModel):
    """Result of QFT."""
    n_qubits: int
    input_state: List[int]
    inverse: bool
    counts: Dict[str, int]
    probabilities: Dict[str, float]
    shots: int


class DeutschJozsaRequest(BaseModel):
    """Request to run Deutsch-Jozsa algorithm."""
    n_qubits: int = Field(..., ge=1, le=8)
    oracle_type: Literal["constant_0", "constant_1", "balanced"]
    shots: int = 1024


class DeutschJozsaResponse(BaseModel):
    """Result of Deutsch-Jozsa algorithm."""
    oracle_type: str
    detected_type: str
    correct: bool
    counts: Dict[str, int]
    shots: int
    zero_probability: float


class TeleportationRequest(BaseModel):
    """Request for quantum teleportation demo."""
    state_theta: float = 0  # Bloch sphere theta
    state_phi: float = 0    # Bloch sphere phi
    shots: int = 1024


class TeleportationResponse(BaseModel):
    """Result of teleportation."""
    input_bloch: Dict[str, float]
    output_bloch: Dict[str, float]
    fidelity: float
    counts: Dict[str, int]
    shots: int


# =============================================================================
# Export/Import Models
# =============================================================================

class OpenQASMExport(BaseModel):
    """OpenQASM export response."""
    circuit_id: str
    qasm: str
    version: str = "2.0"


class OpenQASMImport(BaseModel):
    """OpenQASM import request."""
    qasm: str


# =============================================================================
# Error Models
# =============================================================================

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
