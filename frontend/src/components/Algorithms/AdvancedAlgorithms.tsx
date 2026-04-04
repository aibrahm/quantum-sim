import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  runQPE, runVQE, runQAOA, runQEC,
  type QPEResponse, type VQEResponse, type QAOAResponse, type QECResponse,
} from '../../api/client';

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
      <div className="text-gray-400 uppercase font-bold text-[10px] tracking-wider">QUANTUM PHASE ESTIMATION</div>
      <div className="text-gray-600 text-[10px]">
        Estimate eigenphase of U|ψ⟩ = e^{'{2πiθ}'}|ψ⟩
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">BITS</span>
          <input type="range" min={2} max={8} value={nPrecision}
            onChange={(e) => setNPrecision(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right">{nPrecision}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">PHASE</span>
          <input type="range" min={0} max={1} step={0.01} value={phase}
            onChange={(e) => setPhase(parseFloat(e.target.value))} className="flex-1" />
          <span className="w-12 text-right">{phase.toFixed(2)}</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="w-full py-2 bg-accent text-white font-bold uppercase disabled:bg-gray-200 disabled:text-gray-400">
        {mutation.isPending ? 'ESTIMATING...' : 'ESTIMATE'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-200">
          <div className="flex justify-between">
            <span className="text-gray-500">DOMINANT</span>
            <span className="font-bold">{result.dominant_phase.toFixed(4)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">TRUE θ</span>
            <span>{result.true_phases.map(p => p.toFixed(4)).join(', ')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">RESOLUTION</span>
            <span>1/{Math.pow(2, nPrecision)}</span>
          </div>
          <div className="pt-2">
            <div className="text-gray-500 mb-1">PHASE DISTRIBUTION</div>
            {Object.entries(result.estimated_phases)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 4)
              .map(([ph, prob]) => (
                <div key={ph} className="flex items-center gap-2">
                  <span className="text-gray-500 w-12">{parseFloat(ph).toFixed(3)}</span>
                  <div className="flex-1 h-3 border border-gray-200 bg-gray-50">
                    <div className="h-full bar-fill" style={{ width: `${prob * 100}%` }} />
                  </div>
                  <span className="w-10 text-right text-gray-400">{(prob * 100).toFixed(0)}%</span>
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
      <div className="text-gray-400 uppercase font-bold text-[10px] tracking-wider">VARIATIONAL QUANTUM EIGENSOLVER</div>
      <div className="text-gray-600 text-[10px]">
        H₂ ground state energy — hybrid quantum-classical optimization
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">BOND</span>
          <input type="range" min={0.3} max={2.5} step={0.01} value={bondLength}
            onChange={(e) => setBondLength(parseFloat(e.target.value))} className="flex-1" />
          <span className="w-12 text-right">{bondLength.toFixed(2)}Å</span>
        </div>

        <div>
          <span className="text-gray-500">ANSATZ</span>
          <div className="flex gap-1 mt-1">
            {[
              { value: 'uccsd', label: 'UCCSD' },
              { value: 'hardware_efficient', label: 'HW-EFF' },
            ].map((opt) => (
              <button key={opt.value}
                onClick={() => setAnsatz(opt.value as typeof ansatz)}
                className={`flex-1 py-1 border font-bold ${
                  ansatz === opt.value ? 'border-accent bg-accent text-white' : 'border-qborder hover:border-accent'
                }`}>
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">ITERS</span>
          <input type="range" min={50} max={300} step={10} value={maxIter}
            onChange={(e) => setMaxIter(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right">{maxIter}</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="w-full py-2 bg-accent text-white font-bold uppercase disabled:bg-gray-200 disabled:text-gray-400">
        {mutation.isPending ? 'OPTIMIZING...' : 'FIND GROUND STATE'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-200">
          <div className="flex justify-between">
            <span className="text-gray-500">VQE ENERGY</span>
            <span className="font-bold">{result.ground_energy.toFixed(6)} Ha</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">EXACT</span>
            <span>{result.exact_energy.toFixed(6)} Ha</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">ERROR</span>
            <span>{(result.error * 1000).toFixed(3)} mHa</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">CHEM ACC</span>
            <span className={result.chemical_accuracy ? 'text-accent font-bold' : 'text-gray-500'}>
              {result.chemical_accuracy ? 'YES (< 1.6 mHa)' : 'NO'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">ITERATIONS</span>
            <span>{result.iterations}</span>
          </div>

          {/* Convergence mini-chart */}
          <div className="pt-2">
            <div className="text-gray-500 mb-1">CONVERGENCE</div>
            <div className="h-16 flex items-end gap-[1px]">
              {result.convergence_history
                .filter((_, i) => i % Math.max(1, Math.floor(result.convergence_history.length / 40)) === 0)
                .map((e, i, arr) => {
                  const min = Math.min(...arr);
                  const max = Math.max(...arr);
                  const range = max - min || 1;
                  const h = ((e - min) / range) * 100;
                  return (
                    <div key={i} className="flex-1 bg-gray-700" style={{ height: `${100 - h}%` }}>
                      <div className="w-full bg-white" style={{ height: `${h}%` }} />
                    </div>
                  );
                })}
            </div>
            <div className="flex justify-between text-gray-600 text-[9px] mt-1">
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
      <div className="text-gray-400 uppercase font-bold text-[10px] tracking-wider">QAOA — MAXCUT</div>
      <div className="text-gray-600 text-[10px]">
        Quantum optimization for graph partitioning
      </div>

      <div className="space-y-2">
        <div>
          <span className="text-gray-500">GRAPH</span>
          <div className="flex gap-1 mt-1">
            {Object.entries(PRESET_GRAPHS).map(([key, val]) => (
              <button key={key}
                onClick={() => { setGraph(key as keyof typeof PRESET_GRAPHS); setResult(null); }}
                className={`flex-1 py-1 border font-bold ${
                  graph === key ? 'border-accent bg-accent text-white' : 'border-qborder hover:border-accent'
                }`}>
                {val.label}
              </button>
            ))}
          </div>
        </div>

        <div className="text-gray-600 text-[10px]">
          {g.n} vertices, {g.edges.length} edges
        </div>

        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">LAYERS</span>
          <input type="range" min={1} max={4} value={pLayers}
            onChange={(e) => setPLayers(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right">p={pLayers}</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="w-full py-2 bg-accent text-white font-bold uppercase disabled:bg-gray-200 disabled:text-gray-400">
        {mutation.isPending ? 'OPTIMIZING...' : 'RUN QAOA'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-200">
          <div className="flex justify-between">
            <span className="text-gray-500">BEST CUT</span>
            <span className="font-bold">|{result.best_bitstring}⟩ = {result.best_cost.toFixed(1)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">EXACT</span>
            <span>|{result.exact_solution}⟩ = {result.exact_cost.toFixed(1)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">APPROX RATIO</span>
            <span className="font-bold">{(result.approximation_ratio * 100).toFixed(1)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">γ*</span>
            <span>{result.optimal_gammas.map(g => g.toFixed(2)).join(', ')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">β*</span>
            <span>{result.optimal_betas.map(b => b.toFixed(2)).join(', ')}</span>
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
      <div className="text-gray-400 uppercase font-bold text-[10px] tracking-wider">QUANTUM ERROR CORRECTION</div>
      <div className="text-gray-600 text-[10px]">
        Protect quantum information against decoherence
      </div>

      <div className="space-y-2">
        <div>
          <span className="text-gray-500">CODE</span>
          <div className="flex gap-1 mt-1">
            {[
              { value: 'bit_flip', label: '3Q BIT' },
              { value: 'phase_flip', label: '3Q PHASE' },
              { value: 'shor', label: 'SHOR 9Q' },
            ].map((opt) => (
              <button key={opt.value}
                onClick={() => { setCode(opt.value as typeof code); setResult(null); }}
                className={`flex-1 py-1 border font-bold ${
                  code === opt.value ? 'border-accent bg-accent text-white' : 'border-qborder hover:border-accent'
                }`}>
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-2">
          <div className="flex-1">
            <span className="text-gray-500">LOGICAL</span>
            <div className="flex gap-1 mt-1">
              {(['0', '1'] as const).map((s) => (
                <button key={s} onClick={() => setLogicalState(s)}
                  className={`flex-1 py-1 border font-bold ${
                    logicalState === s ? 'border-accent bg-accent text-white' : 'border-gray-600'
                  }`}>
                  |{s}⟩
                </button>
              ))}
            </div>
          </div>
          <div className="flex-1">
            <span className="text-gray-500">ERROR</span>
            <div className="flex gap-1 mt-1">
              {(['X', 'Z', 'none'] as const).map((e) => (
                <button key={e} onClick={() => setErrorType(e)}
                  className={`flex-1 py-1 border font-bold ${
                    errorType === e ? 'border-accent bg-accent text-white' : 'border-gray-600'
                  }`}>
                  {e === 'none' ? '—' : e}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">ERR Q#</span>
          <input type="range" min={0} max={maxQubit} value={Math.min(errorQubit, maxQubit)}
            onChange={(e) => setErrorQubit(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right">{Math.min(errorQubit, maxQubit)}</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="w-full py-2 bg-accent text-white font-bold uppercase disabled:bg-gray-200 disabled:text-gray-400">
        {mutation.isPending ? 'RUNNING...' : 'TEST CODE'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-200">
          <div className="text-gray-400 font-bold">{result.code_name.toUpperCase()}</div>
          <div className="grid grid-cols-2 gap-2">
            <div className="border border-gray-200 p-2">
              <div className="text-gray-600">PHYSICAL</div>
              <div className="font-bold">{result.n_physical}Q</div>
            </div>
            <div className="border border-gray-200 p-2">
              <div className="text-gray-600">LOGICAL</div>
              <div className="font-bold">{result.n_logical}Q</div>
            </div>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">ERROR</span>
            <span>{result.error_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">SYNDROME</span>
            <span className="font-mono">{result.syndrome}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">CORRECTED</span>
            <span className={`font-bold ${result.corrected ? 'text-white' : 'text-gray-500'}`}>
              {result.corrected ? 'YES' : 'NO'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">FIDELITY</span>
            <span className="font-bold">{(result.fidelity * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
