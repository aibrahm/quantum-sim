import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  runGrover,
  runDeutschJozsa,
  runQFT,
  runTeleportation,
  type GroverResponse,
  type DeutschJozsaResponse,
  type QFTResponse,
  type TeleportationResponse,
} from '../../api/client';
import { QPEPanel, VQEPanel, QAOAPanel, QECPanel } from './AdvancedAlgorithms';

type AlgorithmTab = 'grover' | 'dj' | 'qft' | 'teleport' | 'qpe' | 'vqe' | 'qaoa' | 'qec';

export function AlgorithmsPanel() {
  const [activeTab, setActiveTab] = useState<AlgorithmTab>('grover');

  const tabs: { id: AlgorithmTab; label: string }[] = [
    { id: 'grover', label: 'Grover' },
    { id: 'dj', label: 'D–J' },
    { id: 'qft', label: 'QFT' },
    { id: 'teleport', label: 'Teleport' },
    { id: 'qpe', label: 'QPE' },
    { id: 'vqe', label: 'VQE' },
    { id: 'qaoa', label: 'QAOA' },
    { id: 'qec', label: 'QEC' },
  ];

  const tabButton = (tab: { id: AlgorithmTab; label: string }) => (
    <button
      key={tab.id}
      onClick={() => setActiveTab(tab.id)}
      className={`relative flex-1 px-1 py-2 text-[12px] transition-colors duration-[70ms] ${
        activeTab === tab.id
          ? 'text-gray-100 font-medium'
          : 'text-gray-70 hover:text-gray-100'
      }`}
    >
      {tab.label}
      {activeTab === tab.id && (
        <span className="absolute inset-x-0 bottom-0 h-[2px] bg-blue-60" />
      )}
    </button>
  );

  return (
    <div className="h-full flex flex-col">
      {/* Tabs — two rows for all algorithms */}
      <div className="border-b border-line">
        <div className="flex">{tabs.slice(0, 4).map(tabButton)}</div>
        <div className="flex border-t border-line">{tabs.slice(4).map(tabButton)}</div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'grover' && <GroverPanel />}
        {activeTab === 'dj' && <DeutschJozsaPanel />}
        {activeTab === 'qft' && <QFTPanel />}
        {activeTab === 'teleport' && <TeleportationPanel />}
        {activeTab === 'qpe' && <QPEPanel />}
        {activeTab === 'vqe' && <VQEPanel />}
        {activeTab === 'qaoa' && <QAOAPanel />}
        {activeTab === 'qec' && <QECPanel />}
      </div>
    </div>
  );
}

function GroverPanel() {
  const [nQubits, setNQubits] = useState(3);
  const [markedState, setMarkedState] = useState(5);
  const [result, setResult] = useState<GroverResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => runGrover({ n_qubits: nQubits, marked_states: [markedState] }),
    onSuccess: setResult,
  });

  const maxState = Math.pow(2, nQubits) - 1;

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">Grover's search</div>
      <div className="text-gray-50 text-[11px]">
        Find a marked state in O(√N) queries
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="field-label w-16">Qubits</span>
          <input
            type="range"
            min={2}
            max={6}
            value={nQubits}
            onChange={(e) => {
              const n = parseInt(e.target.value);
              setNQubits(n);
              setMarkedState(Math.min(markedState, Math.pow(2, n) - 1));
            }}
            className="flex-1"
          />
          <span className="w-8 text-right font-mono tabular-nums">{nQubits}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="field-label w-16">Target</span>
          <input
            type="number"
            min={0}
            max={maxState}
            value={markedState}
            onChange={(e) => setMarkedState(Math.min(maxState, Math.max(0, parseInt(e.target.value) || 0)))}
            className="flex-1 px-2 py-1"
          />
          <span className="text-gray-50 w-16 text-right font-mono tabular-nums">/{maxState}</span>
        </div>
      </div>

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="btn-primary w-full py-2"
      >
        {mutation.isPending ? 'Searching…' : 'Search'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="flex justify-between">
            <span className="text-gray-50">Success</span>
            <span className="font-mono font-medium tabular-nums">{(result.success_probability * 100).toFixed(1)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Iterations</span>
            <span className="font-mono tabular-nums">{result.iterations_used}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Optimal</span>
            <span className="font-mono tabular-nums">{result.optimal_iterations}</span>
          </div>
          <div className="pt-2">
            <div className="text-gray-50 mb-1">Top results</div>
            {Object.entries(result.counts)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 4)
              .map(([state, count]) => (
                <div key={state} className="flex justify-between text-gray-70 font-mono tabular-nums">
                  <span>|{state}⟩</span>
                  <span>{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DeutschJozsaPanel() {
  const [nQubits, setNQubits] = useState(3);
  const [oracleType, setOracleType] = useState<'constant_0' | 'constant_1' | 'balanced'>('balanced');
  const [result, setResult] = useState<DeutschJozsaResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => runDeutschJozsa({ n_qubits: nQubits, oracle_type: oracleType }),
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">Deutsch–Jozsa</div>
      <div className="text-gray-50 text-[11px]">
        Determine if f(x) is constant or balanced in one query
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="field-label w-16">Qubits</span>
          <input type="range" min={1} max={6} value={nQubits}
            onChange={(e) => setNQubits(parseInt(e.target.value))} className="flex-1" />
          <span className="w-8 text-right font-mono tabular-nums">{nQubits}</span>
        </div>

        <div>
          <span className="field-label">Oracle</span>
          <div className="flex gap-1 mt-1">
            {[
              { value: 'constant_0', label: 'f=0' },
              { value: 'constant_1', label: 'f=1' },
              { value: 'balanced', label: 'Balanced' },
            ].map((opt) => (
              <button key={opt.value}
                onClick={() => setOracleType(opt.value as typeof oracleType)}
                className={`flex-1 py-1 border rounded-[2px] transition-colors duration-[70ms] ${
                  oracleType === opt.value
                    ? 'border-blue-60 bg-blue-10 text-blue-60 font-medium'
                    : 'border-line text-gray-70 hover:bg-gray-10'
                }`}>
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Running…' : 'Run'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="flex justify-between">
            <span className="text-gray-50">Oracle</span>
            <span className="font-mono">{result.oracle_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Detected</span>
            <span className="font-mono">{result.detected_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">Correct</span>
            <span className="font-mono">{result.correct ? 'Yes' : 'No'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-50">P(0…0)</span>
            <span className="font-mono tabular-nums">{(result.zero_probability * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

function QFTPanel() {
  const [nQubits, setNQubits] = useState(3);
  const [inputState, setInputState] = useState([1, 0, 0]);
  const [inverse, setInverse] = useState(false);
  const [result, setResult] = useState<QFTResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => runQFT({ n_qubits: nQubits, input_state: inputState.slice(0, nQubits), inverse }),
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">Quantum Fourier transform</div>
      <div className="text-gray-50 text-[11px]">Transform to the frequency domain</div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="field-label w-16">Qubits</span>
          <input type="range" min={2} max={5} value={nQubits}
            onChange={(e) => { const n = parseInt(e.target.value); setNQubits(n); setInputState(Array(n).fill(0)); }}
            className="flex-1" />
          <span className="w-8 text-right font-mono tabular-nums">{nQubits}</span>
        </div>

        <div>
          <span className="field-label">Input state</span>
          <div className="flex gap-1 mt-1">
            {Array.from({ length: nQubits }, (_, i) => (
              <button key={i}
                onClick={() => { const next = [...inputState]; next[i] = next[i] === 0 ? 1 : 0; setInputState(next); }}
                className={`flex-1 py-1 border rounded-[2px] font-mono transition-colors duration-[70ms] ${
                  inputState[i] === 1
                    ? 'border-blue-60 bg-blue-10 text-blue-60 font-medium'
                    : 'border-line text-gray-70 hover:bg-gray-10'
                }`}>
                {inputState[i]}
              </button>
            ))}
          </div>
        </div>

        <label className="flex items-center gap-2">
          <input type="checkbox" checked={inverse} onChange={(e) => setInverse(e.target.checked)} />
          <span className="field-label">Inverse QFT</span>
        </label>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Running…' : 'Run QFT'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="text-gray-50 mb-1">Output distribution</div>
          {Object.entries(result.counts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 6)
            .map(([state, count]) => (
              <div key={state} className="flex items-center gap-2">
                <span className="font-mono w-12 tabular-nums">|{state}⟩</span>
                <div className="flex-1 h-3 bar-track">
                  <div className="h-full bar-fill" style={{ width: `${(count / result.shots) * 100}%` }} />
                </div>
                <span className="w-10 text-right text-gray-70 font-mono tabular-nums">{((count / result.shots) * 100).toFixed(0)}%</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

function TeleportationPanel() {
  const [theta, setTheta] = useState(Math.PI / 4);
  const [phi, setPhi] = useState(0);
  const [result, setResult] = useState<TeleportationResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => runTeleportation({ state_theta: theta, state_phi: phi }),
    onSuccess: setResult,
  });

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">Quantum teleportation</div>
      <div className="text-gray-50 text-[11px]">Transfer a state using entanglement</div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="field-label w-8">θ</span>
          <input type="range" min={0} max={Math.PI} step={0.01} value={theta}
            onChange={(e) => setTheta(parseFloat(e.target.value))} className="flex-1" />
          <span className="w-12 text-right font-mono tabular-nums">{(theta / Math.PI).toFixed(2)}π</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="field-label w-8">φ</span>
          <input type="range" min={0} max={2 * Math.PI} step={0.01} value={phi}
            onChange={(e) => setPhi(parseFloat(e.target.value))} className="flex-1" />
          <span className="w-12 text-right font-mono tabular-nums">{(phi / Math.PI).toFixed(2)}π</span>
        </div>
      </div>

      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
        className="btn-primary w-full py-2">
        {mutation.isPending ? 'Teleporting…' : 'Teleport'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="flex justify-between">
            <span className="text-gray-50">Fidelity</span>
            <span className="font-mono font-medium tabular-nums">{(result.fidelity * 100).toFixed(1)}%</span>
          </div>
          <div>
            <div className="text-gray-50 mb-1">Input Bloch vector</div>
            <div className="grid grid-cols-3 gap-1 text-center">
              {(['x', 'y', 'z'] as const).map((axis) => (
                <div key={axis} className="stat p-1">
                  <div className="text-gray-50">{axis.toUpperCase()}</div>
                  <div className="font-mono tabular-nums">{result.input_bloch[axis].toFixed(2)}</div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="text-gray-50 mb-1">Output Bloch vector</div>
            <div className="grid grid-cols-3 gap-1 text-center">
              {(['x', 'y', 'z'] as const).map((axis) => (
                <div key={axis} className="stat p-1">
                  <div className="text-gray-50">{axis.toUpperCase()}</div>
                  <div className="font-mono tabular-nums">{result.output_bloch[axis].toFixed(2)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
