// Gate types
export type SingleQubitGate =
  | 'I' | 'X' | 'Y' | 'Z' | 'H' | 'S' | 'Sdg' | 'T' | 'Tdg' | 'SX' | 'SXdg';

export type RotationGate =
  | 'Rx' | 'Ry' | 'Rz' | 'Phase' | 'U1' | 'U2' | 'U3';

export type TwoQubitGate =
  | 'CX' | 'CY' | 'CZ' | 'SWAP' | 'iSWAP' | 'CRx' | 'CRy' | 'CRz' | 'CPhase'
  | 'Rxx' | 'Ryy' | 'Rzz';

export type ThreeQubitGate = 'CCX' | 'CSWAP';

export type GateName = SingleQubitGate | RotationGate | TwoQubitGate | ThreeQubitGate;

// Gate operation
export interface GateOperation {
  gate_name: GateName;
  qubits: number[];
  params: number[];
  label?: string;
}

// Measurement operation
export interface MeasurementOperation {
  qubits: number[];
  classical_bits: number[];
  basis: 'X' | 'Y' | 'Z';
}

// Circuit operation
export interface CircuitOperation {
  type: 'gate' | 'measurement' | 'barrier' | 'reset';
  gate?: GateOperation;
  measurement?: MeasurementOperation;
  qubits: number[];
}

// Circuit
export interface Circuit {
  id: string;
  n_qubits: number;
  n_classical: number;
  name: string;
  operations: CircuitOperation[];
  depth: number;
  gate_count: Record<string, number>;
}

// Bloch vector
export interface BlochVector {
  qubit: number;
  x: number;
  y: number;
  z: number;
}

// State snapshot
export interface StateSnapshot {
  step: number;
  operation_type: string;
  operation_name: string;
  qubits: number[];
  params: number[];
  probabilities: number[];
  bloch_vectors: BlochVector[];
  amplitudes_real?: number[];
  amplitudes_imag?: number[];
  measurement_outcome?: number;
}

// Execution result
export interface ExecutionResult {
  circuit_id: string;
  counts: Record<string, number>;
  shots: number;
  probabilities: Record<string, number>;
  execution_time_ms: number;
  snapshots: StateSnapshot[];
}

// State vector response
export interface StateVectorResponse {
  circuit_id: string;
  n_qubits: number;
  amplitudes_real: number[];
  amplitudes_imag: number[];
  probabilities: number[];
  bloch_vectors: BlochVector[];
}

// Noise configuration
export interface NoiseConfig {
  depolarizing_rate?: number;
  amplitude_damping?: number;
  phase_damping?: number;
  readout_error?: Record<number, [number, number]>;
}

// Execution request
export interface ExecutionRequest {
  shots: number;
  mode: 'statevector' | 'density_matrix';
  noise?: NoiseConfig;
  record_snapshots: boolean;
}

// Gate family color code (functional grouping, IBM-Composer style)
export type GateFamily = 'pauli' | 'hadamard' | 'phase' | 'rotation' | 'controlled' | 'measure';

export interface GateFamilyMeta {
  label: string;
  fill: string; // solid tile fill (flat, no border, no glow)
  text: string; // tile label color, picked per-contrast
}

export const GATE_FAMILIES: Record<GateFamily, GateFamilyMeta> = {
  pauli:      { label: 'Pauli',       fill: '#4589ff', text: '#ffffff' },
  hadamard:   { label: 'Hadamard',    fill: '#fa4d56', text: '#ffffff' },
  phase:      { label: 'Phase',       fill: '#a56eff', text: '#ffffff' },
  rotation:   { label: 'Rotation',    fill: '#009d9a', text: '#161616' },
  controlled: { label: 'Controlled',  fill: '#24a148', text: '#ffffff' },
  measure:    { label: 'Measurement', fill: '#8d8d8d', text: '#161616' },
};

// Gate metadata for UI
export interface GateInfo {
  name: GateName;
  displayName: string;
  description: string;
  numQubits: number;
  numParams: number;
  paramNames?: string[];
  color: string;
  family: GateFamily;
  symbol: string;
}

// Gate palette categories
export const GATE_CATEGORIES = {
  basic: {
    name: 'Basic',
    gates: ['I', 'X', 'Y', 'Z', 'H', 'S', 'T'] as GateName[],
  },
  rotation: {
    name: 'Rotation',
    gates: ['Rx', 'Ry', 'Rz', 'Phase'] as GateName[],
  },
  controlled: {
    name: 'Controlled',
    gates: ['CX', 'CY', 'CZ', 'CRx', 'CRy', 'CRz'] as GateName[],
  },
  entangling: {
    name: 'Entangling',
    gates: ['SWAP', 'iSWAP', 'CCX', 'CSWAP'] as GateName[],
  },
};

// Gate info lookup — color = family color (see GATE_FAMILIES)
export const GATE_INFO: Record<GateName, GateInfo> = {
  I: { name: 'I', displayName: 'Identity', description: 'Identity gate', numQubits: 1, numParams: 0, color: '#4589ff', family: 'pauli', symbol: 'I' },
  X: { name: 'X', displayName: 'Pauli-X', description: 'NOT gate, bit flip', numQubits: 1, numParams: 0, color: '#4589ff', family: 'pauli', symbol: 'X' },
  Y: { name: 'Y', displayName: 'Pauli-Y', description: 'Y rotation by π', numQubits: 1, numParams: 0, color: '#4589ff', family: 'pauli', symbol: 'Y' },
  Z: { name: 'Z', displayName: 'Pauli-Z', description: 'Phase flip', numQubits: 1, numParams: 0, color: '#4589ff', family: 'pauli', symbol: 'Z' },
  H: { name: 'H', displayName: 'Hadamard', description: 'Creates superposition', numQubits: 1, numParams: 0, color: '#fa4d56', family: 'hadamard', symbol: 'H' },
  S: { name: 'S', displayName: 'S Gate', description: 'π/2 phase', numQubits: 1, numParams: 0, color: '#a56eff', family: 'phase', symbol: 'S' },
  Sdg: { name: 'Sdg', displayName: 'S†', description: '-π/2 phase', numQubits: 1, numParams: 0, color: '#a56eff', family: 'phase', symbol: 'S†' },
  T: { name: 'T', displayName: 'T Gate', description: 'π/4 phase', numQubits: 1, numParams: 0, color: '#a56eff', family: 'phase', symbol: 'T' },
  Tdg: { name: 'Tdg', displayName: 'T†', description: '-π/4 phase', numQubits: 1, numParams: 0, color: '#a56eff', family: 'phase', symbol: 'T†' },
  SX: { name: 'SX', displayName: '√X', description: 'Square root of X', numQubits: 1, numParams: 0, color: '#4589ff', family: 'pauli', symbol: '√X' },
  SXdg: { name: 'SXdg', displayName: '√X†', description: 'Inverse √X', numQubits: 1, numParams: 0, color: '#4589ff', family: 'pauli', symbol: '√X†' },
  Rx: { name: 'Rx', displayName: 'Rx(θ)', description: 'X-axis rotation', numQubits: 1, numParams: 1, paramNames: ['θ'], color: '#009d9a', family: 'rotation', symbol: 'Rx' },
  Ry: { name: 'Ry', displayName: 'Ry(θ)', description: 'Y-axis rotation', numQubits: 1, numParams: 1, paramNames: ['θ'], color: '#009d9a', family: 'rotation', symbol: 'Ry' },
  Rz: { name: 'Rz', displayName: 'Rz(θ)', description: 'Z-axis rotation', numQubits: 1, numParams: 1, paramNames: ['θ'], color: '#a56eff', family: 'phase', symbol: 'Rz' },
  Phase: { name: 'Phase', displayName: 'P(θ)', description: 'Phase gate', numQubits: 1, numParams: 1, paramNames: ['θ'], color: '#a56eff', family: 'phase', symbol: 'P' },
  U1: { name: 'U1', displayName: 'U1(λ)', description: 'U1 gate', numQubits: 1, numParams: 1, paramNames: ['λ'], color: '#a56eff', family: 'phase', symbol: 'U1' },
  U2: { name: 'U2', displayName: 'U2(φ,λ)', description: 'U2 gate', numQubits: 1, numParams: 2, paramNames: ['φ', 'λ'], color: '#009d9a', family: 'rotation', symbol: 'U2' },
  U3: { name: 'U3', displayName: 'U3(θ,φ,λ)', description: 'Universal gate', numQubits: 1, numParams: 3, paramNames: ['θ', 'φ', 'λ'], color: '#009d9a', family: 'rotation', symbol: 'U3' },
  CX: { name: 'CX', displayName: 'CNOT', description: 'Controlled-X', numQubits: 2, numParams: 0, color: '#24a148', family: 'controlled', symbol: '⊕' },
  CY: { name: 'CY', displayName: 'CY', description: 'Controlled-Y', numQubits: 2, numParams: 0, color: '#24a148', family: 'controlled', symbol: 'CY' },
  CZ: { name: 'CZ', displayName: 'CZ', description: 'Controlled-Z', numQubits: 2, numParams: 0, color: '#24a148', family: 'controlled', symbol: 'CZ' },
  SWAP: { name: 'SWAP', displayName: 'SWAP', description: 'Swap qubits', numQubits: 2, numParams: 0, color: '#24a148', family: 'controlled', symbol: '×' },
  iSWAP: { name: 'iSWAP', displayName: 'iSWAP', description: 'iSWAP gate', numQubits: 2, numParams: 0, color: '#24a148', family: 'controlled', symbol: 'i×' },
  CRx: { name: 'CRx', displayName: 'CRx(θ)', description: 'Controlled Rx', numQubits: 2, numParams: 1, paramNames: ['θ'], color: '#24a148', family: 'controlled', symbol: 'CRx' },
  CRy: { name: 'CRy', displayName: 'CRy(θ)', description: 'Controlled Ry', numQubits: 2, numParams: 1, paramNames: ['θ'], color: '#24a148', family: 'controlled', symbol: 'CRy' },
  CRz: { name: 'CRz', displayName: 'CRz(θ)', description: 'Controlled Rz', numQubits: 2, numParams: 1, paramNames: ['θ'], color: '#24a148', family: 'controlled', symbol: 'CRz' },
  CPhase: { name: 'CPhase', displayName: 'CP(θ)', description: 'Controlled Phase', numQubits: 2, numParams: 1, paramNames: ['θ'], color: '#a56eff', family: 'phase', symbol: 'CP' },
  Rxx: { name: 'Rxx', displayName: 'Rxx(θ)', description: 'XX rotation', numQubits: 2, numParams: 1, paramNames: ['θ'], color: '#009d9a', family: 'rotation', symbol: 'Rxx' },
  Ryy: { name: 'Ryy', displayName: 'Ryy(θ)', description: 'YY rotation', numQubits: 2, numParams: 1, paramNames: ['θ'], color: '#009d9a', family: 'rotation', symbol: 'Ryy' },
  Rzz: { name: 'Rzz', displayName: 'Rzz(θ)', description: 'ZZ rotation', numQubits: 2, numParams: 1, paramNames: ['θ'], color: '#009d9a', family: 'rotation', symbol: 'Rzz' },
  CCX: { name: 'CCX', displayName: 'Toffoli', description: 'CC-NOT gate', numQubits: 3, numParams: 0, color: '#24a148', family: 'controlled', symbol: '⊕' },
  CSWAP: { name: 'CSWAP', displayName: 'Fredkin', description: 'Controlled SWAP', numQubits: 3, numParams: 0, color: '#24a148', family: 'controlled', symbol: 'C×' },
};
