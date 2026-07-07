import { useState } from 'react';
import { GATE_CATEGORIES, GATE_FAMILIES, GATE_INFO, type GateName } from '../../types';
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
      <div className="mb-3">
        <div className="field-label mb-2">Qubits</div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setNQubits(Math.max(1, nQubits - 1))}
            disabled={nQubits <= 1}
            className="btn-secondary w-8 h-8 text-sm"
          >
            −
          </button>
          <span className="panel flex-1 h-8 flex items-center justify-center text-sm font-mono tabular-nums">
            {nQubits}
          </span>
          <button
            onClick={() => setNQubits(Math.min(10, nQubits + 1))}
            disabled={nQubits >= 10}
            className="btn-secondary w-8 h-8 text-sm"
          >
            +
          </button>
        </div>
      </div>

      {/* Initial states */}
      <div className="mb-3">
        <div className="field-label mb-2">Initial state</div>
        <div className="space-y-1">
          {Array.from({ length: nQubits }, (_, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-gray-70 w-7 font-mono tabular-nums">q{i}</span>
              <div className="flex flex-1 border border-line rounded-[2px] overflow-hidden">
                {INIT_STATES.map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => setInitialState(i, value)}
                    className={`flex-1 py-1 text-[11px] font-mono transition-colors duration-[70ms] ${
                      initialStates[i] === value
                        ? 'bg-blue-10 text-blue-60 font-medium'
                        : 'bg-white text-gray-70 hover:bg-gray-10'
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
      <div className="text-[11px] text-gray-50 mb-2">Drag gates to the circuit</div>

      {/* Gate categories */}
      <div className="space-y-2">
        {Object.entries(GATE_CATEGORIES).map(([key, category]) => (
          <div key={key} className="panel overflow-hidden">
            <button
              onClick={() => toggleCategory(key)}
              className="w-full flex items-center justify-between px-2 py-1.5 text-left hover:bg-gray-10 transition-colors duration-[70ms]"
            >
              <span className="field-label">{category.name}</span>
              <span className="text-gray-50">{expandedCategories.has(key) ? '−' : '+'}</span>
            </button>

            {expandedCategories.has(key) && (
              <div className="p-2 grid grid-cols-4 gap-1 border-t border-line">
                {category.gates.map((gate) => {
                  const info = GATE_INFO[gate];
                  const fam = GATE_FAMILIES[info.family];
                  const isSelected = selectedGate === gate;
                  return (
                    <button
                      key={gate}
                      draggable
                      onDragStart={(e) => handleDragStart(e, gate)}
                      onClick={() => handleGateClick(gate)}
                      title={`${info.description} (drag to circuit)`}
                      className="aspect-square flex items-center justify-center text-[11px] font-mono font-medium rounded-[2px] cursor-grab active:cursor-grabbing transition-[filter] duration-[70ms] hover:brightness-95"
                      style={{
                        background: fam.fill,
                        color: fam.text,
                        outline: isSelected ? '2px solid #0f62fe' : 'none',
                        outlineOffset: 1,
                      }}
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

      {/* Family legend */}
      <div className="mt-3">
        <div className="field-label mb-1.5">Gate families</div>
        <div className="grid grid-cols-2 gap-x-2 gap-y-1">
          {Object.entries(GATE_FAMILIES).map(([key, fam]) => (
            <div key={key} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-[1px] shrink-0"
                style={{ background: fam.fill }}
              />
              <span className="text-[11px] text-gray-70">{fam.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Selected gate configuration */}
      {selectedGate && (
        <div className="mt-3 p-2 panel">
          <div className="text-[13px] font-semibold mb-1">
            {GATE_INFO[selectedGate].displayName}
          </div>
          <div className="text-gray-50 mb-2 text-[11px]">
            {GATE_INFO[selectedGate].description}
          </div>

          {/* Target qubits */}
          <div className="space-y-1 mb-2">
            {targetQubits.map((q, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="field-label w-12">
                  {GATE_INFO[selectedGate].numQubits === 2 && idx === 0
                    ? 'Control'
                    : `q${idx}`}
                </span>
                <select
                  value={q}
                  onChange={(e) => {
                    const next = [...targetQubits];
                    next[idx] = parseInt(e.target.value);
                    setTargetQubits(next);
                  }}
                  className="flex-1 px-1 py-0.5"
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
                  <span className="text-gray-70 w-12">
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
                  <span className="w-10 text-right font-mono tabular-nums">
                    {(p / Math.PI).toFixed(2)}π
                  </span>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={handleAddGate}
            className="btn-primary w-full py-1.5"
          >
            Add
          </button>
        </div>
      )}

      {/* Quick actions */}
      <div className="mt-3 space-y-1">
        <button
          onClick={handleAddMeasurement}
          className="btn-secondary w-full py-1.5"
        >
          Measure all
        </button>
        <button
          onClick={() => addBarrier(Array.from({ length: nQubits }, (_, i) => i))}
          className="btn-secondary w-full py-1.5"
        >
          Barrier
        </button>
      </div>
    </div>
  );
}
