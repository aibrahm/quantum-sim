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
      <div className="flex border-b border-line">
        {[
          { id: 'optimize', label: 'Optimize' },
          { id: 'entangle', label: 'Entanglement' },
        ].map((tab) => (
          <button key={tab.id}
            onClick={() => setActiveTab(tab.id as ToolTab)}
            className={`relative flex-1 px-3 py-2.5 text-[13px] transition-colors duration-[70ms] ${
              activeTab === tab.id
                ? 'text-gray-100 font-medium'
                : 'text-gray-70 hover:text-gray-100'
            }`}>
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute inset-x-0 bottom-0 h-[2px] bg-blue-60" />
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-4">
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
      <div className="text-[13px] font-semibold">Circuit optimizer</div>
      <div className="text-gray-50 text-[11px]">
        Multi-pass compiler-style quantum circuit optimization
      </div>

      <div className="stat p-2 space-y-1 text-[11px] text-gray-70">
        <div>Passes: gate cancellation, single-qubit fusion,</div>
        <div>commutation analysis, CX optimization, rotation merging</div>
      </div>

      <div className="text-gray-50 text-[11px]">
        Current circuit: {operations.length} operations
      </div>

      <button onClick={() => mutation.mutate()}
        disabled={mutation.isPending || operations.length === 0}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Optimizing…' : 'Optimize'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="text-[13px] font-semibold">Results</div>

          {/* Before/After comparison */}
          <div className="grid grid-cols-2 gap-2">
            <div className="stat p-2 text-center">
              <div className="text-gray-50">Before</div>
              <div className="font-mono font-medium text-lg tabular-nums">{result.original_gates}</div>
              <div className="text-gray-50 text-[11px]">gates</div>
            </div>
            <div className="stat p-2 text-center border border-blue-60">
              <div className="text-gray-50">After</div>
              <div className="font-mono font-medium text-lg tabular-nums text-blue-60">{result.optimized_gates}</div>
              <div className="text-gray-50 text-[11px]">gates</div>
            </div>
          </div>

          {/* Reduction bar */}
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-gray-50">Reduction</span>
              <span className="font-mono font-medium tabular-nums">{result.gate_reduction_percent.toFixed(1)}%</span>
            </div>
            <div className="h-3 bar-track">
              <div className="h-full bar-fill" style={{ width: `${result.gate_reduction_percent}%` }} />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-50">Depth</span>
              <span className="font-mono tabular-nums">{result.original_depth} → {result.optimized_depth}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-50">CX gates</span>
              <span className="font-mono tabular-nums">{result.original_cx} → {result.optimized_cx}</span>
            </div>
          </div>

          {result.passes_applied.length > 0 && (
            <div className="pt-2">
              <div className="text-gray-50 mb-1">Passes applied</div>
              {result.passes_applied.map((pass, i) => (
                <div key={i} className="text-gray-70 text-[11px]">• {pass}</div>
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
      <div className="text-[13px] font-semibold">Entanglement analysis</div>
      <div className="text-gray-50 text-[11px]">
        Schmidt decomposition, entropy, concurrence
      </div>

      <button onClick={() => mutation.mutate()}
        disabled={mutation.isPending || operations.length === 0}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Analyzing…' : 'Analyze'}
      </button>

      {result && (
        <div className="space-y-3 pt-2 border-t border-line">
          {/* Summary */}
          <div className="grid grid-cols-2 gap-2">
            <div className="stat p-2 text-center">
              <div className="text-gray-50">Entangled</div>
              <div className={`font-medium ${result.is_entangled ? 'text-green-50' : 'text-gray-50'}`}>
                {result.is_entangled ? 'Yes' : 'No'}
              </div>
            </div>
            <div className="stat p-2 text-center">
              <div className="text-gray-50">Schmidt rank</div>
              <div className="font-mono font-medium tabular-nums">{result.schmidt_rank ?? '—'}</div>
            </div>
          </div>

          {/* Concurrence (2-qubit) */}
          {result.concurrence !== undefined && result.concurrence !== null && (
            <div className="flex justify-between">
              <span className="text-gray-50">Concurrence</span>
              <span className="font-mono font-medium tabular-nums">{result.concurrence.toFixed(4)}</span>
            </div>
          )}

          {/* Entanglement fraction */}
          {result.entanglement_fraction !== undefined && result.entanglement_fraction !== null && (
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-50">Ent. fraction</span>
                <span className="font-mono tabular-nums">{(result.entanglement_fraction * 100).toFixed(1)}%</span>
              </div>
              <div className="h-3 bar-track">
                <div className="h-full bar-fill" style={{ width: `${result.entanglement_fraction * 100}%` }} />
              </div>
            </div>
          )}

          {/* Half-chain entropy */}
          {result.half_chain_entropy !== undefined && result.half_chain_entropy !== null && (
            <div className="flex justify-between">
              <span className="text-gray-50">Half-chain S</span>
              <span className="font-mono tabular-nums">{result.half_chain_entropy.toFixed(4)} bits</span>
            </div>
          )}

          {/* Per-qubit entropies */}
          <div>
            <div className="text-gray-50 mb-1">Single-qubit entropies</div>
            {result.single_qubit_entropies.map((s, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <span className="text-gray-70 w-6 font-mono">q{i}</span>
                <div className="flex-1 h-2 bar-track">
                  <div className="h-full bar-fill" style={{ width: `${Math.min(s, 1) * 100}%` }} />
                </div>
                <span className="text-gray-70 w-12 text-right font-mono tabular-nums">{s.toFixed(3)}</span>
              </div>
            ))}
          </div>

          {/* Pairwise entanglement heatmap */}
          {result.pairwise_map.length > 0 && (
            <div>
              <div className="text-gray-50 mb-1">Pairwise entanglement</div>
              <div className="inline-grid gap-[1px]"
                style={{ gridTemplateColumns: `24px repeat(${result.n_qubits}, 1fr)` }}>
                {/* Header */}
                <div />
                {Array.from({ length: result.n_qubits }, (_, i) => (
                  <div key={`h${i}`} className="text-center text-gray-50 text-[10px] w-7 font-mono">q{i}</div>
                ))}
                {/* Rows */}
                {result.pairwise_map.map((row, i) => (
                  <>
                    <div key={`r${i}`} className="text-gray-50 text-[10px] flex items-center font-mono">q{i}</div>
                    {row.map((val, j) => {
                      const intensity = Math.min(val, 1);
                      const bg = i === j ? '#f4f4f4' : `rgba(15, 98, 254, ${intensity * 0.85})`;
                      return (
                        <div key={`${i}-${j}`} className="w-7 h-7 border border-line flex items-center justify-center text-[9px] font-mono tabular-nums"
                          style={{ backgroundColor: bg, color: intensity > 0.5 ? '#ffffff' : '#525252' }}
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
              <div className="text-gray-50 mb-1">Schmidt coefficients</div>
              <div className="flex gap-1">
                {result.schmidt_coefficients.slice(0, 8).map((c, i) => (
                  <div key={i} className="flex-1 text-center">
                    <div className="h-12 flex items-end justify-center bar-track">
                      <div className="w-full bar-fill" style={{ height: `${c * 100}%` }} />
                    </div>
                    <div className="text-[9px] text-gray-50 mt-1 font-mono">λ{i}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Entanglement spectrum */}
          {result.entanglement_spectrum.length > 0 && (
            <div>
              <div className="text-gray-50 mb-1">Entanglement spectrum</div>
              <div className="text-gray-70 text-[11px] font-mono tabular-nums">
                {result.entanglement_spectrum.slice(0, 6).map(e => e.toFixed(3)).join(', ')}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
