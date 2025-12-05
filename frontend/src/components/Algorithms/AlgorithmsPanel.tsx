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

type AlgorithmTab = 'grover' | 'dj' | 'qft' | 'teleport';

export function AlgorithmsPanel() {
  const [activeTab, setActiveTab] = useState<AlgorithmTab>('grover');

  return (
    <div className="h-full flex flex-col">
      {/* Tabs */}
      <div className="flex border-b border-white">
        {[
          { id: 'grover', label: 'GROVER' },
          { id: 'dj', label: 'D-J' },
          { id: 'qft', label: 'QFT' },
          { id: 'teleport', label: 'TELEPORT' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as AlgorithmTab)}
            className={`flex-1 px-2 py-2 text-xs font-bold uppercase ${
              activeTab === tab.id
                ? 'bg-white text-black'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {activeTab === 'grover' && <GroverPanel />}
        {activeTab === 'dj' && <DeutschJozsaPanel />}
        {activeTab === 'qft' && <QFTPanel />}
        {activeTab === 'teleport' && <TeleportationPanel />}
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
      <div className="text-gray-500 uppercase">GROVER'S SEARCH</div>
      <div className="text-gray-600 text-[10px]">
        Find marked state in O(√N) queries
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">QUBITS</span>
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
          <span className="w-8 text-right">{nQubits}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">TARGET</span>
          <input
            type="number"
            min={0}
            max={maxState}
            value={markedState}
            onChange={(e) => setMarkedState(Math.min(maxState, Math.max(0, parseInt(e.target.value) || 0)))}
            className="flex-1 bg-black border border-gray-600 px-2 py-1"
          />
          <span className="text-gray-600 w-16 text-right">/{maxState}</span>
        </div>
      </div>

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="w-full py-2 bg-white text-black font-bold uppercase disabled:bg-gray-600"
      >
        {mutation.isPending ? 'SEARCHING...' : 'SEARCH'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-700">
          <div className="flex justify-between">
            <span className="text-gray-500">SUCCESS</span>
            <span className="font-bold">{(result.success_probability * 100).toFixed(1)}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">ITERATIONS</span>
            <span>{result.iterations_used}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">OPTIMAL</span>
            <span>{result.optimal_iterations}</span>
          </div>
          <div className="pt-2">
            <div className="text-gray-500 mb-1">TOP RESULTS</div>
            {Object.entries(result.counts)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 4)
              .map(([state, count]) => (
                <div key={state} className="flex justify-between text-gray-400">
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
      <div className="text-gray-500 uppercase">DEUTSCH-JOZSA</div>
      <div className="text-gray-600 text-[10px]">
        Determine if f(x) is constant or balanced in 1 query
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">QUBITS</span>
          <input
            type="range"
            min={1}
            max={6}
            value={nQubits}
            onChange={(e) => setNQubits(parseInt(e.target.value))}
            className="flex-1"
          />
          <span className="w-8 text-right">{nQubits}</span>
        </div>

        <div>
          <span className="text-gray-500">ORACLE</span>
          <div className="flex gap-1 mt-1">
            {[
              { value: 'constant_0', label: 'f=0' },
              { value: 'constant_1', label: 'f=1' },
              { value: 'balanced', label: 'BAL' },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => setOracleType(opt.value as typeof oracleType)}
                className={`flex-1 py-1 border font-bold ${
                  oracleType === opt.value
                    ? 'border-white bg-white text-black'
                    : 'border-gray-600 hover:border-white'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="w-full py-2 bg-white text-black font-bold uppercase disabled:bg-gray-600"
      >
        {mutation.isPending ? 'RUNNING...' : 'RUN'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-700">
          <div className="flex justify-between">
            <span className="text-gray-500">ORACLE</span>
            <span>{result.oracle_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">DETECTED</span>
            <span className={result.correct ? 'text-white' : 'text-gray-400'}>
              {result.detected_type.toUpperCase()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">CORRECT</span>
            <span>{result.correct ? 'YES' : 'NO'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">P(0...0)</span>
            <span>{(result.zero_probability * 100).toFixed(1)}%</span>
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
      <div className="text-gray-500 uppercase">QUANTUM FOURIER TRANSFORM</div>
      <div className="text-gray-600 text-[10px]">
        Transform to frequency domain
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-16">QUBITS</span>
          <input
            type="range"
            min={2}
            max={5}
            value={nQubits}
            onChange={(e) => {
              const n = parseInt(e.target.value);
              setNQubits(n);
              setInputState(Array(n).fill(0));
            }}
            className="flex-1"
          />
          <span className="w-8 text-right">{nQubits}</span>
        </div>

        <div>
          <span className="text-gray-500">INPUT STATE</span>
          <div className="flex gap-1 mt-1">
            {Array.from({ length: nQubits }, (_, i) => (
              <button
                key={i}
                onClick={() => {
                  const next = [...inputState];
                  next[i] = next[i] === 0 ? 1 : 0;
                  setInputState(next);
                }}
                className={`flex-1 py-1 border font-bold ${
                  inputState[i] === 1
                    ? 'border-white bg-white text-black'
                    : 'border-gray-600'
                }`}
              >
                {inputState[i]}
              </button>
            ))}
          </div>
        </div>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={inverse}
            onChange={(e) => setInverse(e.target.checked)}
          />
          <span className="text-gray-500">INVERSE QFT</span>
        </label>
      </div>

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="w-full py-2 bg-white text-black font-bold uppercase disabled:bg-gray-600"
      >
        {mutation.isPending ? 'RUNNING...' : 'RUN QFT'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-700">
          <div className="text-gray-500 mb-1">OUTPUT DISTRIBUTION</div>
          {Object.entries(result.counts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 6)
            .map(([state, count]) => (
              <div key={state} className="flex items-center gap-2">
                <span className="text-gray-500 w-12">|{state}⟩</span>
                <div className="flex-1 h-3 border border-gray-700 bg-black">
                  <div
                    className="h-full bg-white"
                    style={{ width: `${(count / result.shots) * 100}%` }}
                  />
                </div>
                <span className="w-10 text-right text-gray-400">
                  {((count / result.shots) * 100).toFixed(0)}%
                </span>
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
      <div className="text-gray-500 uppercase">QUANTUM TELEPORTATION</div>
      <div className="text-gray-600 text-[10px]">
        Transfer state using entanglement
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-8">θ</span>
          <input
            type="range"
            min={0}
            max={Math.PI}
            step={0.01}
            value={theta}
            onChange={(e) => setTheta(parseFloat(e.target.value))}
            className="flex-1"
          />
          <span className="w-12 text-right">{(theta / Math.PI).toFixed(2)}π</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-gray-500 w-8">φ</span>
          <input
            type="range"
            min={0}
            max={2 * Math.PI}
            step={0.01}
            value={phi}
            onChange={(e) => setPhi(parseFloat(e.target.value))}
            className="flex-1"
          />
          <span className="w-12 text-right">{(phi / Math.PI).toFixed(2)}π</span>
        </div>
      </div>

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="w-full py-2 bg-white text-black font-bold uppercase disabled:bg-gray-600"
      >
        {mutation.isPending ? 'TELEPORTING...' : 'TELEPORT'}
      </button>

      {result && (
        <div className="space-y-2 pt-2 border-t border-gray-700">
          <div className="flex justify-between">
            <span className="text-gray-500">FIDELITY</span>
            <span className="font-bold">{(result.fidelity * 100).toFixed(1)}%</span>
          </div>

          <div>
            <div className="text-gray-500 mb-1">INPUT BLOCH</div>
            <div className="grid grid-cols-3 gap-1 text-center">
              <div className="border border-gray-700 p-1">
                <div className="text-gray-600">X</div>
                <div>{result.input_bloch.x.toFixed(2)}</div>
              </div>
              <div className="border border-gray-700 p-1">
                <div className="text-gray-600">Y</div>
                <div>{result.input_bloch.y.toFixed(2)}</div>
              </div>
              <div className="border border-gray-700 p-1">
                <div className="text-gray-600">Z</div>
                <div>{result.input_bloch.z.toFixed(2)}</div>
              </div>
            </div>
          </div>

          <div>
            <div className="text-gray-500 mb-1">OUTPUT BLOCH</div>
            <div className="grid grid-cols-3 gap-1 text-center">
              <div className="border border-gray-700 p-1">
                <div className="text-gray-600">X</div>
                <div>{result.output_bloch.x.toFixed(2)}</div>
              </div>
              <div className="border border-gray-700 p-1">
                <div className="text-gray-600">Y</div>
                <div>{result.output_bloch.y.toFixed(2)}</div>
              </div>
              <div className="border border-gray-700 p-1">
                <div className="text-gray-600">Z</div>
                <div>{result.output_bloch.z.toFixed(2)}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
