import { useState } from 'react';
import { GATE_CATEGORIES, GATE_INFO, type GateName } from '../../types';
import { useCircuitStore, type QubitInitState } from '../../stores/circuitStore';

const INIT_STATES: { value: QubitInitState; label: string }[] = [
  { value: '0', label: '|0⟩' },
  { value: '1', label: '|1⟩' },
  { value: '+', label: '|+⟩' },
  { value: '-', label: '|−⟩' },
];

export function GatePalette() {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['basic', 'controlled'])
  );
  const [selectedGate, setSelectedGate] = useState<GateName | null>(null);
  const [params, setParams] = useState<number[]>([Math.PI / 2]);
  const [targetQubits, setTargetQubits] = useState<number[]>([0]);

  const {
    nQubits,
    setNQubits,
    addGate,
    addMeasurement,
    addBarrier,
    initialStates,
    setInitialState,
  } = useCircuitStore();

  const toggleCategory = (category: string) => {
    const next = new Set(expandedCategories);
    if (next.has(category)) {
      next.delete(category);
    } else {
      next.add(category);
    }
    setExpandedCategories(next);
  };

  const handleGateClick = (gate: GateName) => {
    const info = GATE_INFO[gate];
    setSelectedGate(gate);

    if (info.numParams > 0) {
      setParams(Array(info.numParams).fill(Math.PI / 2));
    } else {
      setParams([]);
    }

    setTargetQubits(Array(info.numQubits).fill(0).map((_, i) => i % nQubits));
  };

  const handleAddGate = () => {
    if (!selectedGate) return;
    addGate(selectedGate, targetQubits, params);
    setSelectedGate(null);
  };

  const handleAddMeasurement = () => {
    for (let i = 0; i < nQubits; i++) {
      addMeasurement(i, i);
    }
  };

  const handleDragStart = (e: React.DragEvent, gate: GateName) => {
    e.dataTransfer.setData('gate', gate);
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <div className="p-3 text-xs">
      {/* Qubit count control */}
      <div className="mb-4 border border-gray-600 p-2">
        <div className="text-gray-500 uppercase mb-2">QUBITS</div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setNQubits(Math.max(1, nQubits - 1))}
            disabled={nQubits <= 1}
            className="w-8 h-8 border border-white disabled:border-gray-600 disabled:text-gray-600 font-bold"
          >
            -
          </button>
          <span className="w-8 text-center text-lg font-bold">{nQubits}</span>
          <button
            onClick={() => setNQubits(Math.min(10, nQubits + 1))}
            disabled={nQubits >= 10}
            className="w-8 h-8 border border-white disabled:border-gray-600 disabled:text-gray-600 font-bold"
          >
            +
          </button>
        </div>
      </div>

      {/* Initial states */}
      <div className="mb-4 border border-gray-600 p-2">
        <div className="text-gray-500 uppercase mb-2">INIT STATE</div>
        <div className="space-y-1">
          {Array.from({ length: nQubits }, (_, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-gray-500 w-8">q{i}</span>
              <div className="flex gap-1 flex-1">
                {INIT_STATES.map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => setInitialState(i, value)}
                    className={`flex-1 py-1 border font-bold ${
                      initialStates[i] === value
                        ? 'border-white bg-white text-black'
                        : 'border-gray-600 hover:border-white'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Drag hint */}
      <div className="mb-2 text-gray-600 text-[10px] uppercase">
        DRAG GATES TO CIRCUIT
      </div>

      {/* Gate categories */}
      <div className="space-y-1">
        {Object.entries(GATE_CATEGORIES).map(([key, category]) => (
          <div key={key} className="border border-gray-600">
            <button
              onClick={() => toggleCategory(key)}
              className="w-full flex items-center justify-between px-2 py-1 text-left hover:bg-gray-900"
            >
              <span className="uppercase font-bold">{category.name}</span>
              <span>{expandedCategories.has(key) ? '−' : '+'}</span>
            </button>

            {expandedCategories.has(key) && (
              <div className="p-2 grid grid-cols-4 gap-1 border-t border-gray-600">
                {category.gates.map((gate) => {
                  const info = GATE_INFO[gate];
                  return (
                    <button
                      key={gate}
                      draggable
                      onDragStart={(e) => handleDragStart(e, gate)}
                      onClick={() => handleGateClick(gate)}
                      title={`${info.description} (drag to circuit)`}
                      className={`aspect-square flex items-center justify-center text-[10px] font-bold border cursor-grab active:cursor-grabbing ${
                        selectedGate === gate
                          ? 'border-white bg-white text-black'
                          : 'border-gray-600 hover:border-white'
                      }`}
                    >
                      {info.symbol}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Selected gate configuration */}
      {selectedGate && (
        <div className="mt-3 p-2 border border-white">
          <div className="font-bold uppercase mb-1">{GATE_INFO[selectedGate].displayName}</div>
          <div className="text-gray-500 mb-2">
            {GATE_INFO[selectedGate].description}
          </div>

          {/* Target qubits */}
          <div className="space-y-1 mb-2">
            {targetQubits.map((q, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="text-gray-500 w-12 uppercase">
                  {GATE_INFO[selectedGate].numQubits === 2 && idx === 0
                    ? 'CTRL'
                    : `Q${idx}`}
                </span>
                <select
                  value={q}
                  onChange={(e) => {
                    const next = [...targetQubits];
                    next[idx] = parseInt(e.target.value);
                    setTargetQubits(next);
                  }}
                  className="flex-1 bg-black border border-gray-600 px-1 py-0.5"
                >
                  {Array.from({ length: nQubits }, (_, i) => (
                    <option key={i} value={i}>
                      q{i}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          {/* Parameters */}
          {GATE_INFO[selectedGate].numParams > 0 && (
            <div className="space-y-1 mb-2">
              {params.map((p, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="text-gray-500 w-12">
                    {GATE_INFO[selectedGate].paramNames?.[idx] || `θ${idx + 1}`}
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={2 * Math.PI}
                    step={0.01}
                    value={p}
                    onChange={(e) => {
                      const next = [...params];
                      next[idx] = parseFloat(e.target.value);
                      setParams(next);
                    }}
                    className="flex-1"
                  />
                  <span className="text-gray-400 w-10 text-right">
                    {(p / Math.PI).toFixed(2)}π
                  </span>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={handleAddGate}
            className="w-full py-1 bg-white text-black font-bold uppercase"
          >
            ADD
          </button>
        </div>
      )}

      {/* Quick actions */}
      <div className="mt-3 space-y-1">
        <button
          onClick={handleAddMeasurement}
          className="w-full py-1 border border-gray-600 hover:border-white font-bold uppercase"
        >
          MEASURE ALL
        </button>
        <button
          onClick={() => addBarrier(Array.from({ length: nQubits }, (_, i) => i))}
          className="w-full py-1 border border-gray-600 hover:border-white font-bold uppercase"
        >
          BARRIER
        </button>
      </div>
    </div>
  );
}
