import axios from 'axios';
import type {
  Circuit,
  CircuitOperation,
  ExecutionRequest,
  ExecutionResult,
  StateVectorResponse,
  BlochVector,
} from '../types';

const API_BASE = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Circuit API
export async function createCircuit(
  nQubits: number,
  name: string,
  operations: CircuitOperation[]
): Promise<Circuit> {
  const response = await api.post('/circuit', {
    n_qubits: nQubits,
    name,
    operations,
  });
  return response.data;
}

export async function getCircuit(circuitId: string): Promise<Circuit> {
  const response = await api.get(`/circuit/${circuitId}`);
  return response.data;
}

export async function updateCircuit(
  circuitId: string,
  operations: CircuitOperation[]
): Promise<Circuit> {
  const response = await api.put(`/circuit/${circuitId}`, { operations });
  return response.data;
}

export async function deleteCircuit(circuitId: string): Promise<void> {
  await api.delete(`/circuit/${circuitId}`);
}

// Execution API
export async function runCircuit(
  circuitId: string,
  request: ExecutionRequest
): Promise<ExecutionResult> {
  const response = await api.post(`/circuit/${circuitId}/run`, request);
  return response.data;
}

export async function getStateVector(
  circuitId: string
): Promise<StateVectorResponse> {
  const response = await api.get(`/circuit/${circuitId}/state`);
  return response.data;
}

export async function getBlochVectors(
  circuitId: string
): Promise<{ circuit_id: string; bloch_vectors: BlochVector[] }> {
  const response = await api.get(`/circuit/${circuitId}/bloch`);
  return response.data;
}

export async function getProbabilities(
  circuitId: string
): Promise<{ circuit_id: string; probabilities: Record<string, number> }> {
  const response = await api.get(`/circuit/${circuitId}/probabilities`);
  return response.data;
}

// Analysis API
export async function getCircuitStats(circuitId: string): Promise<{
  circuit_id: string;
  n_qubits: number;
  depth: number;
  total_gates: number;
  gate_counts: Record<string, number>;
  two_qubit_gates: number;
  measurements: number;
}> {
  const response = await api.get(`/circuit/${circuitId}/stats`);
  return response.data;
}

// Export API
export async function exportOpenQASM(
  circuitId: string,
  version: string = '2.0'
): Promise<{ circuit_id: string; qasm: string; version: string }> {
  const response = await api.get(`/circuit/${circuitId}/openqasm`, {
    params: { version },
  });
  return response.data;
}

// WebSocket for real-time execution
export function createExecutionWebSocket(
  circuitId: string,
  onMessage: (data: unknown) => void,
  onError?: (error: Event) => void,
  onClose?: () => void
): WebSocket {
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/circuit/${circuitId}/execute`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onerror = (event) => {
    console.error('WebSocket error:', event);
    onError?.(event);
  };

  ws.onclose = () => {
    onClose?.();
  };

  return ws;
}

// Health check
export async function healthCheck(): Promise<{ status: string; version: string }> {
  const response = await axios.get(`${API_BASE}/health`);
  return response.data;
}

// Algorithm API

export interface GroverRequest {
  n_qubits: number;
  marked_states: number[];
  iterations?: number;
}

export interface GroverResponse {
  counts: Record<string, number>;
  shots: number;
  iterations_used: number;
  success_probability: number;
  optimal_iterations: number;
}

export async function runGrover(request: GroverRequest): Promise<GroverResponse> {
  const response = await api.post('/algorithms/grover', request);
  return response.data;
}

export interface DeutschJozsaRequest {
  n_qubits: number;
  oracle_type: 'constant_0' | 'constant_1' | 'balanced';
  shots?: number;
}

export interface DeutschJozsaResponse {
  oracle_type: string;
  detected_type: string;
  correct: boolean;
  counts: Record<string, number>;
  shots: number;
  zero_probability: number;
}

export async function runDeutschJozsa(request: DeutschJozsaRequest): Promise<DeutschJozsaResponse> {
  const response = await api.post('/algorithms/deutsch-jozsa', request);
  return response.data;
}

export interface QFTRequest {
  n_qubits: number;
  input_state?: number[];
  inverse?: boolean;
  shots?: number;
}

export interface QFTResponse {
  n_qubits: number;
  input_state: number[];
  inverse: boolean;
  counts: Record<string, number>;
  probabilities: Record<string, number>;
  shots: number;
}

export async function runQFT(request: QFTRequest): Promise<QFTResponse> {
  const response = await api.post('/algorithms/qft', request);
  return response.data;
}

export interface TeleportationRequest {
  state_theta: number;
  state_phi: number;
  shots?: number;
}

export interface TeleportationResponse {
  input_bloch: { x: number; y: number; z: number };
  output_bloch: { x: number; y: number; z: number };
  fidelity: number;
  counts: Record<string, number>;
  shots: number;
}

export async function runTeleportation(request: TeleportationRequest): Promise<TeleportationResponse> {
  const response = await api.post('/algorithms/teleportation', request);
  return response.data;
}

// QPE API
export interface QPERequest {
  n_precision: number;
  unitary_type: 'phase_gate' | 'custom';
  phase?: number;
  shots?: number;
}

export interface QPEResponse {
  estimated_phases: Record<string, number>;
  dominant_phase: number;
  true_phases: number[];
  n_precision: number;
  phase_resolution: number;
  counts: Record<string, number>;
}

export async function runQPE(request: QPERequest): Promise<QPEResponse> {
  const response = await api.post('/algorithms/qpe', request);
  return response.data;
}

// VQE API
export interface VQERequest {
  hamiltonian_type: 'h2' | 'custom';
  bond_length?: number;
  custom_hamiltonian?: { coefficient: number; paulis: string }[];
  ansatz: string;
  max_iterations: number;
  initial_params?: number[];
}

export interface VQEResponse {
  ground_energy: number;
  exact_energy: number;
  error: number;
  chemical_accuracy: boolean;
  optimal_params: number[];
  convergence_history: number[];
  iterations: number;
  ansatz: string;
  hamiltonian: string;
}

export async function runVQE(request: VQERequest): Promise<VQEResponse> {
  const response = await api.post('/algorithms/vqe', request);
  return response.data;
}

// QAOA API
export interface QAOARequest {
  problem_type: 'maxcut' | 'max_independent_set';
  n_vertices: number;
  edges: number[][];
  p_layers: number;
  max_iterations?: number;
  shots?: number;
}

export interface QAOAResponse {
  best_bitstring: string;
  best_cost: number;
  exact_solution: string;
  exact_cost: number;
  approximation_ratio: number;
  optimal_gammas: number[];
  optimal_betas: number[];
  convergence_history: number[];
  p_layers: number;
  problem_name: string;
}

export async function runQAOA(request: QAOARequest): Promise<QAOAResponse> {
  const response = await api.post('/algorithms/qaoa', request);
  return response.data;
}

// QEC API
export interface QECRequest {
  code: 'bit_flip' | 'phase_flip' | 'shor';
  logical_state: '0' | '1';
  error_type: 'X' | 'Y' | 'Z' | 'none';
  error_qubit: number;
}

export interface QECResponse {
  code_name: string;
  n_physical: number;
  n_logical: number;
  error_type: string;
  error_qubit: number;
  syndrome: string;
  corrected: boolean;
  fidelity: number;
  logical_state: string;
}

export async function runQEC(request: QECRequest): Promise<QECResponse> {
  const response = await api.post('/algorithms/qec', request);
  return response.data;
}

// Entanglement API
export interface EntanglementResponse {
  n_qubits: number;
  single_qubit_entropies: number[];
  total_entanglement: number;
  half_chain_entropy?: number;
  pairwise_map: number[][];
  schmidt_rank?: number;
  schmidt_coefficients?: number[];
  is_entangled?: boolean;
  entanglement_fraction?: number;
  concurrence?: number;
  entanglement_spectrum: number[];
}

export async function getEntanglement(circuitId: string): Promise<EntanglementResponse> {
  const response = await api.get(`/circuit/${circuitId}/entanglement`);
  return response.data;
}

// Optimization API
export interface OptimizationResponse {
  circuit_id: string;
  original_depth: number;
  optimized_depth: number;
  original_gates: number;
  optimized_gates: number;
  original_cx: number;
  optimized_cx: number;
  gate_reduction_percent: number;
  passes_applied: string[];
}

export async function optimizeCircuit(circuitId: string): Promise<OptimizationResponse> {
  const response = await api.post(`/circuit/${circuitId}/optimize`, { iterations: 3 });
  return response.data;
}

// QSVT Research API
export interface QSVTDemoResponse {
  framework: Record<string, string>;
  grover: Record<string, string>;
  phase_estimation: Record<string, string>;
  hhl: Record<string, unknown>;
  hamiltonian_sim: Record<string, unknown>;
}

export async function getQSVTDemo(): Promise<QSVTDemoResponse> {
  const response = await api.get('/research/qsvt');
  return response.data;
}
