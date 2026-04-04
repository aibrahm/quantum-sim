import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useCircuitStore } from '../../stores/circuitStore';
import {
  createCircuit, optimizeCircuit, getEntanglement,
  type OptimizationResponse, type EntanglementResponse,
} from '../../api/client';

type ToolTab = 'optimize' | 'entangle';

export function ToolsPanel() {
  const [activeTab, setActiveTab] = useState<ToolTab>('optimize');

  return (
    <div className="h-full flex flex-col">
      <div className="flex border-b border-qborder">
        {[
          { id: 'optimize', label: 'OPTIMIZE' },
          { id: 'entangle', label: 'ENTANGLE' },
        ].map((tab) => (
          <button key={tab.id}
            onClick={() => setActiveTab(tab.id as ToolTab)}
            className={`flex-1 px-3 py-2 text-xs font-bold uppercase ${
              activeTab === tab.id ? 'bg-accent text-white' : 'text-gray-400 hover:text-accent'
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-3">
        {activeTab === 'optimize' && <OptimizerPanel />}
        {activeTab === 'entangle' && <EntanglementPanel />}
      </div>
    </div>
  );
}

// =============================================================================
// Circuit Optimizer
// =============================================================================

function OptimizerPanel() {
  const { nQubits, name, toOperationsPayload, operations, circuitId, setCircuitId } = useCircuitStore();
  const [result, setResult] = useState<OptimizationResponse | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      let id = circuitId;
      if (!id) {
        const circuit = await createCircuit(nQubits, name, toOperationsPayload());
        id = circuit.id;
        setCircuitId(id);
      }
      return optimizeCircuit(id);
    },
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-gray-500 uppercase font-bold">CIRCUIT OPTIMIZER</div>
      <div className="text-gray-600 text-[10px]">
        Multi-pass compiler-style quantum circuit optimization
      </div>

      <div className="border border-gray-200 p-2 space-y-1 text-[10px] text-gray-500">
        <div>PASSES: Gate cancellation, single-qubit fusion,</div>
        <div>commutation analysis, CX optimization, rotation merging</div>
      </div>

      <div className="text-gray-600 text-[10px]">
        Current circuit: {operations.length} operations
      </div>

      <button onClick={() => mutation.mutate()}
        disabled={mutation.isPending || operations.length === 0}
        className="w-full py-2 bg-accent text-white font-bold uppercase disabled:bg-gray-200 disabled:text-gray-400">
        {mutation.isPending ? 'OPTIMIZING...' : 'OPTIMIZE'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-200">
          <div className="text-gray-400 font-bold uppercase">RESULTS</div>

          {/* Before/After comparison */}
          <div className="grid grid-cols-2 gap-2">
            <div className="border border-gray-200 p-2 text-center">
              <div className="text-gray-600">BEFORE</div>
              <div className="font-bold text-lg">{result.original_gates}</div>
              <div className="text-gray-600 text-[10px]">gates</div>
            </div>
            <div className="border border-accent p-2 text-center">
              <div className="text-gray-600">AFTER</div>
              <div className="font-bold text-lg">{result.optimized_gates}</div>
              <div className="text-gray-600 text-[10px]">gates</div>
            </div>
          </div>

          {/* Reduction bar */}
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-gray-500">REDUCTION</span>
              <span className="font-bold">{result.gate_reduction_percent.toFixed(1)}%</span>
            </div>
            <div className="h-3 border border-gray-200 bg-gray-50">
              <div className="h-full bar-fill" style={{ width: `${result.gate_reduction_percent}%` }} />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-500">DEPTH</span>
              <span>{result.original_depth} → {result.optimized_depth}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">CX GATES</span>
              <span>{result.original_cx} → {result.optimized_cx}</span>
            </div>
          </div>

          {result.passes_applied.length > 0 && (
            <div className="pt-2">
              <div className="text-gray-500 mb-1">PASSES APPLIED</div>
              {result.passes_applied.map((pass, i) => (
                <div key={i} className="text-gray-600 text-[10px]">• {pass}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Entanglement Analysis
// =============================================================================

function EntanglementPanel() {
  const { nQubits, name, toOperationsPayload, operations, circuitId, setCircuitId } = useCircuitStore();
  const [result, setResult] = useState<EntanglementResponse | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      let id = circuitId;
      if (!id) {
        const circuit = await createCircuit(nQubits, name, toOperationsPayload());
        id = circuit.id;
        setCircuitId(id);
      }
      return getEntanglement(id);
    },
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-gray-500 uppercase font-bold">ENTANGLEMENT ANALYSIS</div>
      <div className="text-gray-600 text-[10px]">
        Schmidt decomposition, entropy, concurrence
      </div>

      <button onClick={() => mutation.mutate()}
        disabled={mutation.isPending || operations.length === 0}
        className="w-full py-2 bg-accent text-white font-bold uppercase disabled:bg-gray-200 disabled:text-gray-400">
        {mutation.isPending ? 'ANALYZING...' : 'ANALYZE'}
      </button>

      {result && (
        <div className="space-y-3 pt-2 border-t border-gray-200">
          {/* Summary */}
          <div className="grid grid-cols-2 gap-2">
            <div className="border border-gray-200 p-2 text-center">
              <div className="text-gray-600">ENTANGLED</div>
              <div className={`font-bold ${result.is_entangled ? 'text-accent' : 'text-gray-500'}`}>
                {result.is_entangled ? 'YES' : 'NO'}
              </div>
            </div>
            <div className="border border-gray-200 p-2 text-center">
              <div className="text-gray-600">SCHMIDT RANK</div>
              <div className="font-bold">{result.schmidt_rank ?? '—'}</div>
            </div>
          </div>

          {/* Concurrence (2-qubit) */}
          {result.concurrence !== undefined && result.concurrence !== null && (
            <div className="flex justify-between">
              <span className="text-gray-500">CONCURRENCE</span>
              <span className="font-bold">{result.concurrence.toFixed(4)}</span>
            </div>
          )}

          {/* Entanglement fraction */}
          {result.entanglement_fraction !== undefined && result.entanglement_fraction !== null && (
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-500">ENT. FRACTION</span>
                <span>{(result.entanglement_fraction * 100).toFixed(1)}%</span>
              </div>
              <div className="h-3 border border-gray-200 bg-gray-50">
                <div className="h-full bar-fill" style={{ width: `${result.entanglement_fraction * 100}%` }} />
              </div>
            </div>
          )}

          {/* Half-chain entropy */}
          {result.half_chain_entropy !== undefined && result.half_chain_entropy !== null && (
            <div className="flex justify-between">
              <span className="text-gray-500">HALF-CHAIN S</span>
              <span>{result.half_chain_entropy.toFixed(4)} bits</span>
            </div>
          )}

          {/* Per-qubit entropies */}
          <div>
            <div className="text-gray-500 mb-1">SINGLE-QUBIT ENTROPIES</div>
            {result.single_qubit_entropies.map((s, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <span className="text-gray-600 w-6">q{i}</span>
                <div className="flex-1 h-2 border border-gray-200 bg-gray-50">
                  <div className="h-full bar-fill" style={{ width: `${Math.min(s, 1) * 100}%` }} />
                </div>
                <span className="text-gray-500 w-12 text-right">{s.toFixed(3)}</span>
              </div>
            ))}
          </div>

          {/* Pairwise entanglement heatmap */}
          {result.pairwise_map.length > 0 && (
            <div>
              <div className="text-gray-500 mb-1">PAIRWISE ENTANGLEMENT</div>
              <div className="inline-grid gap-[1px]"
                style={{ gridTemplateColumns: `24px repeat(${result.n_qubits}, 1fr)` }}>
                {/* Header */}
                <div />
                {Array.from({ length: result.n_qubits }, (_, i) => (
                  <div key={`h${i}`} className="text-center text-gray-600 text-[9px] w-7">q{i}</div>
                ))}
                {/* Rows */}
                {result.pairwise_map.map((row, i) => (
                  <>
                    <div key={`r${i}`} className="text-gray-600 text-[9px] flex items-center">q{i}</div>
                    {row.map((val, j) => {
                      const intensity = Math.min(val, 1);
                      const bg = i === j ? '#333' : `rgba(255,255,255,${intensity})`;
                      return (
                        <div key={`${i}-${j}`} className="w-7 h-7 border border-gray-800 flex items-center justify-center text-[8px]"
                          style={{ backgroundColor: bg, color: intensity > 0.5 ? '#000' : '#888' }}
                          title={`q${i}-q${j}: ${val.toFixed(3)}`}>
                          {i !== j ? val.toFixed(1) : '—'}
                        </div>
                      );
                    })}
                  </>
                ))}
              </div>
            </div>
          )}

          {/* Schmidt coefficients */}
          {result.schmidt_coefficients && result.schmidt_coefficients.length > 0 && (
            <div>
              <div className="text-gray-500 mb-1">SCHMIDT COEFFICIENTS</div>
              <div className="flex gap-1">
                {result.schmidt_coefficients.slice(0, 8).map((c, i) => (
                  <div key={i} className="flex-1 text-center">
                    <div className="h-12 flex items-end justify-center">
                      <div className="w-full bar-fill" style={{ height: `${c * 100}%` }} />
                    </div>
                    <div className="text-[8px] text-gray-600 mt-1">λ{i}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Entanglement spectrum */}
          {result.entanglement_spectrum.length > 0 && (
            <div>
              <div className="text-gray-500 mb-1">ENTANGLEMENT SPECTRUM</div>
              <div className="text-gray-600 text-[10px]">
                {result.entanglement_spectrum.slice(0, 6).map(e => e.toFixed(3)).join(', ')}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
