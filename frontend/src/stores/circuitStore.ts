import { create } from 'zustand';
import type { Circuit, CircuitOperation, ExecutionResult, StateSnapshot, BlochVector, GateName } from '../types';

// Initial qubit states
export type QubitInitState = '0' | '1' | '+' | '-';

interface CircuitState {
  // Circuit data
  circuitId: string | null;
  nQubits: number;
  nClassical: number;
  name: string;
  operations: CircuitOperation[];
  initialStates: QubitInitState[];

  // Execution state
  executionState: 'idle' | 'running' | 'paused' | 'complete';
  currentStep: number;
  snapshots: StateSnapshot[];
  result: ExecutionResult | null;

  // Visualization state
  selectedQubit: number | null;
  blochVectors: BlochVector[];
  probabilities: number[];

  // Settings
  mode: 'statevector' | 'density_matrix';
  shots: number;
  recordSnapshots: boolean;

  // Actions
  setCircuitId: (id: string | null) => void;
  setNQubits: (n: number) => void;
  setName: (name: string) => void;
  addOperation: (op: CircuitOperation) => void;
  removeOperation: (index: number) => void;
  updateOperation: (index: number, op: CircuitOperation) => void;
  clearOperations: () => void;
  loadCircuit: (circuit: Circuit) => void;

  // Initial state actions
  setInitialState: (qubit: number, state: QubitInitState) => void;

  // Gate shortcuts
  addGate: (gate: GateName, qubits: number[], params?: number[]) => void;
  addMeasurement: (qubit: number, cbit: number) => void;
  addBarrier: (qubits: number[]) => void;

  // Execution actions
  setExecutionState: (state: 'idle' | 'running' | 'paused' | 'complete') => void;
  setCurrentStep: (step: number) => void;
  addSnapshot: (snapshot: StateSnapshot) => void;
  setResult: (result: ExecutionResult | null) => void;
  resetExecution: () => void;

  // Visualization actions
  setSelectedQubit: (qubit: number | null) => void;
  setBlochVectors: (vectors: BlochVector[]) => void;
  setProbabilities: (probs: number[]) => void;

  // Settings actions
  setMode: (mode: 'statevector' | 'density_matrix') => void;
  setShots: (shots: number) => void;
  setRecordSnapshots: (record: boolean) => void;

  // Utility
  toOperationsPayload: () => CircuitOperation[];
  reset: () => void;
}

// Convert initial state to gate operations
function initStateToOps(qubit: number, state: QubitInitState): CircuitOperation[] {
  switch (state) {
    case '1':
      // |1⟩ = X|0⟩
      return [{
        type: 'gate',
        gate: { gate_name: 'X', qubits: [qubit], params: [] },
        qubits: [qubit],
      }];
    case '+':
      // |+⟩ = H|0⟩
      return [{
        type: 'gate',
        gate: { gate_name: 'H', qubits: [qubit], params: [] },
        qubits: [qubit],
      }];
    case '-':
      // |−⟩ = HX|0⟩ = XH|0⟩ with phase, but simpler: X then H
      return [
        {
          type: 'gate',
          gate: { gate_name: 'X', qubits: [qubit], params: [] },
          qubits: [qubit],
        },
        {
          type: 'gate',
          gate: { gate_name: 'H', qubits: [qubit], params: [] },
          qubits: [qubit],
        },
      ];
    default:
      return [];
  }
}

const initialState = {
  circuitId: null,
  nQubits: 2,
  nClassical: 2,
  name: 'circuit',
  operations: [],
  initialStates: ['0', '0'] as QubitInitState[],
  executionState: 'idle' as const,
  currentStep: 0,
  snapshots: [],
  result: null,
  selectedQubit: null,
  blochVectors: [],
  probabilities: [],
  mode: 'statevector' as const,
  shots: 1024,
  recordSnapshots: true,
};

export const useCircuitStore = create<CircuitState>((set, get) => ({
  ...initialState,

  setCircuitId: (id) => set({ circuitId: id }),

  setNQubits: (n) => set({
    nQubits: n,
    nClassical: n,
    operations: [],
    initialStates: Array(n).fill('0') as QubitInitState[],
    blochVectors: Array(n).fill(null).map((_, i) => ({ qubit: i, x: 0, y: 0, z: 1 })),
    probabilities: Array(2 ** n).fill(0).map((_, i) => i === 0 ? 1 : 0),
  }),

  setName: (name) => set({ name }),

  addOperation: (op) => set((state) => ({
    operations: [...state.operations, op],
  })),

  removeOperation: (index) => set((state) => ({
    operations: state.operations.filter((_, i) => i !== index),
  })),

  updateOperation: (index, op) => set((state) => ({
    operations: state.operations.map((o, i) => i === index ? op : o),
  })),

  clearOperations: () => set({ operations: [] }),

  loadCircuit: (circuit) => set({
    circuitId: circuit.id,
    nQubits: circuit.n_qubits,
    nClassical: circuit.n_classical,
    name: circuit.name,
    operations: circuit.operations,
    initialStates: Array(circuit.n_qubits).fill('0') as QubitInitState[],
    executionState: 'idle',
    currentStep: 0,
    snapshots: [],
    result: null,
  }),

  setInitialState: (qubit, state) => set((s) => {
    const newStates = [...s.initialStates];
    newStates[qubit] = state;
    return { initialStates: newStates };
  }),

  addGate: (gate, qubits, params = []) => {
    const op: CircuitOperation = {
      type: 'gate',
      gate: { gate_name: gate, qubits, params },
      qubits,
    };
    get().addOperation(op);
  },

  addMeasurement: (qubit, cbit) => {
    const op: CircuitOperation = {
      type: 'measurement',
      measurement: { qubits: [qubit], classical_bits: [cbit], basis: 'Z' },
      qubits: [qubit],
    };
    get().addOperation(op);
  },

  addBarrier: (qubits) => {
    const op: CircuitOperation = {
      type: 'barrier',
      qubits,
    };
    get().addOperation(op);
  },

  setExecutionState: (state) => set({ executionState: state }),

  setCurrentStep: (step) => set({ currentStep: step }),

  addSnapshot: (snapshot) => set((state) => ({
    snapshots: [...state.snapshots, snapshot],
    blochVectors: snapshot.bloch_vectors,
    probabilities: snapshot.probabilities,
    currentStep: snapshot.step,
  })),

  setResult: (result) => set({
    result,
    executionState: result ? 'complete' : 'idle',
  }),

  resetExecution: () => set({
    executionState: 'idle',
    currentStep: 0,
    snapshots: [],
    result: null,
    blochVectors: Array(get().nQubits).fill(null).map((_, i) => ({ qubit: i, x: 0, y: 0, z: 1 })),
    probabilities: Array(2 ** get().nQubits).fill(0).map((_, i) => i === 0 ? 1 : 0),
  }),

  setSelectedQubit: (qubit) => set({ selectedQubit: qubit }),

  setBlochVectors: (vectors) => set({ blochVectors: vectors }),

  setProbabilities: (probs) => set({ probabilities: probs }),

  setMode: (mode) => set({ mode }),

  setShots: (shots) => set({ shots }),

  setRecordSnapshots: (record) => set({ recordSnapshots: record }),

  // Build operations with initialization gates prepended
  toOperationsPayload: () => {
    const { initialStates, operations } = get();
    const initOps: CircuitOperation[] = [];

    // Add initialization gates for non-|0⟩ states
    initialStates.forEach((state, qubit) => {
      initOps.push(...initStateToOps(qubit, state));
    });

    return [...initOps, ...operations];
  },

  reset: () => set(initialState),
}));
