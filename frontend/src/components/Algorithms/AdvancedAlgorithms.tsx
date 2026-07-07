import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  runQPE, runVQE, runQAOA, runQEC,
  type QPEResponse, type VQEResponse, type QAOAResponse, type QECResponse,
} from '../../api/client';

const toggleClass = (active: boolean) =>
  `flex-1 py-1 border rounded-[2px] transition-colors duration-[70ms] ${
    active
      ? 'border-blue-60 bg-blue-10 text-blue-60 font-medium'
      : 'border-line text-gray-70 hover:bg-gray-10'
  }`;

// =============================================================================
// QPE Panel
// =============================================================================

export function QPEPanel() {
  const [nPrecision, setNPrecision] = useState(4);
  const [phase, setPhase] = useState(0.25);
  const [result, setResult] = useState<QPEResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => runQPE({ n_precision: nPrecision, unitary_type: 'phase_gate', phase }),
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">Quantum phase estimation</div>
      <div className="text-gray-50 text-[11px]">
        Estimate the eigenphase of U|ψ⟩ = e^{'{2πiθ}'}|ψ⟩
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="field-label w-16">Bits</span>
          <input type="range" min={2} max={8} value={nPrecision}
            onChange={(e) => setNPrecision(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right font-mono tabular-nums">{nPrecision}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="field-label w-16">Phase</span>
          <input type="range" min={0} max={1} step={0.01} value={phase}
            onChange={(e) => setPhase(parseFloat(e.target.value))} className="flex-1" />
          <span className="w-12 text-right font-mono tabular-nums">{phase.toFixed(2)}</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Estimating…' : 'Estimate'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="flex justify-between">
            <span className="text-gray-50">Dominant</span>
            <span className="font-mono font-medium tabular-nums">{result.dominant_phase.toFixed(4)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">True θ</span>
            <span className="font-mono tabular-nums">{result.true_phases.map(p => p.toFixed(4)).join(', ')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Resolution</span>
            <span className="font-mono tabular-nums">1/{Math.pow(2, nPrecision)}</span>
          </div>
          <div className="pt-2">
            <div className="text-gray-50 mb-1">Phase distribution</div>
            {Object.entries(result.estimated_phases)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 4)
              .map(([ph, prob]) => (
                <div key={ph} className="flex items-center gap-2">
                  <span className="font-mono w-12 tabular-nums">{parseFloat(ph).toFixed(3)}</span>
                  <div className="flex-1 h-3 bar-track">
                    <div className="h-full bar-fill" style={{ width: `${prob * 100}%` }} />
                  </div>
                  <span className="w-10 text-right text-gray-70 font-mono tabular-nums">{(prob * 100).toFixed(0)}%</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// VQE Panel
// =============================================================================

export function VQEPanel() {
  const [bondLength, setBondLength] = useState(0.735);
  const [ansatz, setAnsatz] = useState<'uccsd' | 'hardware_efficient'>('uccsd');
  const [maxIter, setMaxIter] = useState(100);
  const [result, setResult] = useState<VQEResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => runVQE({
      hamiltonian_type: 'h2', bond_length: bondLength,
      ansatz, max_iterations: maxIter,
    }),
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">Variational quantum eigensolver</div>
      <div className="text-gray-50 text-[11px]">
        H₂ ground state energy — hybrid quantum-classical optimization
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="field-label w-16">Bond</span>
          <input type="range" min={0.3} max={2.5} step={0.01} value={bondLength}
            onChange={(e) => setBondLength(parseFloat(e.target.value))} className="flex-1" />
          <span className="w-12 text-right font-mono tabular-nums">{bondLength.toFixed(2)}Å</span>
        </div>

        <div>
          <span className="field-label">Ansatz</span>
          <div className="flex gap-1 mt-1">
            {[
              { value: 'uccsd', label: 'UCCSD' },
              { value: 'hardware_efficient', label: 'Hardware-efficient' },
            ].map((opt) => (
              <button key={opt.value}
                onClick={() => setAnsatz(opt.value as typeof ansatz)}
                className={toggleClass(ansatz === opt.value)}>
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="field-label w-16">Iterations</span>
          <input type="range" min={50} max={300} step={10} value={maxIter}
            onChange={(e) => setMaxIter(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right font-mono tabular-nums">{maxIter}</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Optimizing…' : 'Find ground state'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="flex justify-between">
            <span className="text-gray-50">VQE energy</span>
            <span className="font-mono font-medium tabular-nums">{result.ground_energy.toFixed(6)} Ha</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Exact</span>
            <span className="font-mono tabular-nums">{result.exact_energy.toFixed(6)} Ha</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Error</span>
            <span className="font-mono tabular-nums">{(result.error * 1000).toFixed(3)} mHa</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Chemical accuracy</span>
            <span className={result.chemical_accuracy ? 'text-green-50 font-medium' : 'text-gray-50'}>
              {result.chemical_accuracy ? 'Yes (< 1.6 mHa)' : 'No'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Iterations</span>
            <span className="font-mono tabular-nums">{result.iterations}</span>
          </div>

          {/* Convergence mini-chart */}
          <div className="pt-2">
            <div className="text-gray-50 mb-1">Convergence</div>
            <div className="h-16 flex items-end gap-[1px] stat p-1">
              {result.convergence_history
                .filter((_, i) => i % Math.max(1, Math.floor(result.convergence_history.length / 40)) === 0)
                .map((e, i, arr) => {
                  const min = Math.min(...arr);
                  const max = Math.max(...arr);
                  const range = max - min || 1;
                  const h = ((e - min) / range) * 100;
                  return (
                    <div
                      key={i}
                      className="flex-1 bg-blue-60"
                      style={{ height: `${Math.max(100 - h, 4)}%` }}
                    />
                  );
                })}
            </div>
            <div className="flex justify-between text-gray-50 text-[10px] mt-1">
              <span>iter 0</span>
              <span>iter {result.iterations}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// QAOA Panel
// =============================================================================

const PRESET_GRAPHS = {
  triangle: { n: 3, edges: [[0,1],[1,2],[0,2]], label: '△' },
  square: { n: 4, edges: [[0,1],[1,2],[2,3],[0,3]], label: '□' },
  pentagon: { n: 5, edges: [[0,1],[1,2],[2,3],[3,4],[0,4]], label: '⬠' },
  complete4: { n: 4, edges: [[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]], label: 'K₄' },
};

export function QAOAPanel() {
  const [graph, setGraph] = useState<keyof typeof PRESET_GRAPHS>('triangle');
  const [pLayers, setPLayers] = useState(2);
  const [result, setResult] = useState<QAOAResponse | null>(null);

  const g = PRESET_GRAPHS[graph];

  const mutation = useMutation({
    mutationFn: () => runQAOA({
      problem_type: 'maxcut', n_vertices: g.n, edges: g.edges,
      p_layers: pLayers, max_iterations: 100,
    }),
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">QAOA — MaxCut</div>
      <div className="text-gray-50 text-[11px]">
        Quantum optimization for graph partitioning
      </div>

      <div className="space-y-2">
        <div>
          <span className="field-label">Graph</span>
          <div className="flex gap-1 mt-1">
            {Object.entries(PRESET_GRAPHS).map(([key, val]) => (
              <button key={key}
                onClick={() => { setGraph(key as keyof typeof PRESET_GRAPHS); setResult(null); }}
                className={toggleClass(graph === key)}>
                {val.label}
              </button>
            ))}
          </div>
        </div>

        <div className="text-gray-50 text-[11px]">
          {g.n} vertices, {g.edges.length} edges
        </div>

        <div className="flex items-center gap-2">
          <span className="field-label w-16">Layers</span>
          <input type="range" min={1} max={4} value={pLayers}
            onChange={(e) => setPLayers(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right font-mono tabular-nums">p={pLayers}</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Optimizing…' : 'Run QAOA'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="flex justify-between">
            <span className="text-gray-50">Best cut</span>
            <span className="font-mono font-medium tabular-nums">|{result.best_bitstring}⟩ = {result.best_cost.toFixed(1)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Exact</span>
            <span className="font-mono tabular-nums">|{result.exact_solution}⟩ = {result.exact_cost.toFixed(1)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Approx. ratio</span>
            <span className="font-mono font-medium tabular-nums">{(result.approximation_ratio * 100).toFixed(1)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">γ*</span>
            <span className="font-mono tabular-nums">{result.optimal_gammas.map(g => g.toFixed(2)).join(', ')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">β*</span>
            <span className="font-mono tabular-nums">{result.optimal_betas.map(b => b.toFixed(2)).join(', ')}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// QEC Panel
// =============================================================================

export function QECPanel() {
  const [code, setCode] = useState<'bit_flip' | 'phase_flip' | 'shor'>('bit_flip');
  const [logicalState, setLogicalState] = useState<'0' | '1'>('0');
  const [errorType, setErrorType] = useState<'X' | 'Z' | 'none'>('X');
  const [errorQubit, setErrorQubit] = useState(0);
  const [result, setResult] = useState<QECResponse | null>(null);

  const maxQubit = code === 'shor' ? 8 : 2;

  const mutation = useMutation({
    mutationFn: () => runQEC({
      code, logical_state: logicalState,
      error_type: errorType, error_qubit: Math.min(errorQubit, maxQubit),
    }),
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">Quantum error correction</div>
      <div className="text-gray-50 text-[11px]">
        Protect quantum information against decoherence
      </div>

      <div className="space-y-2">
        <div>
          <span className="field-label">Code</span>
          <div className="flex gap-1 mt-1">
            {[
              { value: 'bit_flip', label: '3q bit' },
              { value: 'phase_flip', label: '3q phase' },
              { value: 'shor', label: 'Shor 9q' },
            ].map((opt) => (
              <button key={opt.value}
                onClick={() => { setCode(opt.value as typeof code); setResult(null); }}
                className={toggleClass(code === opt.value)}>
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-2">
          <div className="flex-1">
            <span className="field-label">Logical</span>
            <div className="flex gap-1 mt-1">
              {(['0', '1'] as const).map((s) => (
                <button key={s} onClick={() => setLogicalState(s)}
                  className={toggleClass(logicalState === s)}>
                  |{s}⟩
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1">
            <span className="field-label">Error</span>
            <div className="flex gap-1 mt-1">
              {(['X', 'Z', 'none'] as const).map((e) => (
                <button key={e} onClick={() => setErrorType(e)}
                  className={toggleClass(errorType === e)}>
                  {e === 'none' ? '—' : e}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="field-label w-16">Error qubit</span>
          <input type="range" min={0} max={maxQubit} value={Math.min(errorQubit, maxQubit)}
            onChange={(e) => setErrorQubit(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right font-mono tabular-nums">{Math.min(errorQubit, maxQubit)}</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Running…' : 'Test code'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="font-medium">{result.code_name}</div>
          <div className="grid grid-cols-2 gap-2">
            <div className="stat p-2 text-center">
              <div className="text-gray-50">Physical</div>
              <div className="font-mono font-medium tabular-nums">{result.n_physical}q</div>
            </div>
            <div className="stat p-2 text-center">
              <div className="text-gray-50">Logical</div>
              <div className="font-mono font-medium tabular-nums">{result.n_logical}q</div>
            </div>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Error</span>
            <span className="font-mono">{result.error_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Syndrome</span>
            <span className="font-mono">{result.syndrome}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Corrected</span>
            <span className={result.corrected ? 'text-green-50 font-medium' : 'text-gray-50'}>
              {result.corrected ? 'Yes' : 'No'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Fidelity</span>
            <span className="font-mono font-medium tabular-nums">{(result.fidelity * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
