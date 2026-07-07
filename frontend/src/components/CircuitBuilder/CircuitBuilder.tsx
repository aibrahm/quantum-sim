import { useState, useRef } from 'react';
import { useCircuitStore, type QubitInitState } from '../../stores/circuitStore';
import { GATE_FAMILIES, GATE_INFO, type GateName } from '../../types';

const CELL_WIDTH = 60;
const CELL_HEIGHT = 60;
const WIRE_Y_OFFSET = CELL_HEIGHT / 2;

const WIRE_COLOR = '#161616';
const MEAS = GATE_FAMILIES.measure;

const INIT_LABELS: Record<QubitInitState, string> = {
  '0': '|0⟩',
  '1': '|1⟩',
  '+': '|+⟩',
  '-': '|−⟩',
};

export function CircuitBuilder() {
  const { nQubits, operations, removeOperation, currentStep, executionState, initialStates, addGate } = useCircuitStore();
  const [dropTarget, setDropTarget] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const circuitWidth = Math.max(operations.length + 2, 10) * CELL_WIDTH;

  const getQubitFromY = (clientY: number): number => {
    if (!svgRef.current) return 0;
    const rect = svgRef.current.getBoundingClientRect();
    const y = clientY - rect.top - 20; // Account for padding
    const qubit = Math.floor(y / CELL_HEIGHT);
    return Math.max(0, Math.min(nQubits - 1, qubit));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    const qubit = getQubitFromY(e.clientY);
    setDropTarget(qubit);
  };

  const handleDragLeave = () => {
    setDropTarget(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const gateName = e.dataTransfer.getData('gate') as GateName;
    if (!gateName) return;

    const info = GATE_INFO[gateName];
    const targetQubit = getQubitFromY(e.clientY);

    // Build qubit array based on gate requirements
    const qubits: number[] = [];
    for (let i = 0; i < info.numQubits; i++) {
      const q = (targetQubit + i) % nQubits;
      qubits.push(q);
    }

    // Default params for rotation gates
    const params = info.numParams > 0
      ? Array(info.numParams).fill(Math.PI / 2)
      : [];

    addGate(gateName, qubits, params);
    setDropTarget(null);
  };

  return (
    <div
      className={`circuit-area rounded-[2px] border p-4 overflow-auto transition-colors duration-[70ms] ${
        dropTarget !== null ? 'border-blue-60' : 'border-line'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <svg
        ref={svgRef}
        width={circuitWidth + 100}
        height={nQubits * CELL_HEIGHT + 40}
        className="select-none"
      >
        {/* Drop indicator — plain light blue band under the wires */}
        {dropTarget !== null && (
          <rect
            x={60}
            y={20 + dropTarget * CELL_HEIGHT}
            width={circuitWidth}
            height={CELL_HEIGHT}
            fill="#edf5ff"
            pointerEvents="none"
          />
        )}

        {/* Qubit labels */}
        {Array.from({ length: nQubits }, (_, i) => (
          <g key={`label-${i}`}>
            <text
              x={40}
              y={20 + i * CELL_HEIGHT + WIRE_Y_OFFSET}
              textAnchor="end"
              dominantBaseline="middle"
              fill="#525252"
              className="text-xs"
              style={{ fontFamily: "'IBM Plex Mono', monospace" }}
            >
              q{i}
            </text>
            <text
              x={40}
              y={20 + i * CELL_HEIGHT + WIRE_Y_OFFSET + 14}
              textAnchor="end"
              dominantBaseline="middle"
              fill={initialStates[i] !== '0' ? '#0f62fe' : '#8d8d8d'}
              className="text-[10px]"
              style={{ fontFamily: "'IBM Plex Mono', monospace" }}
            >
              {INIT_LABELS[initialStates[i]] || '|0⟩'}
            </text>
          </g>
        ))}

        {/* Qubit wires — solid black */}
        {Array.from({ length: nQubits }, (_, i) => (
          <line
            key={`wire-${i}`}
            x1={60}
            y1={20 + i * CELL_HEIGHT + WIRE_Y_OFFSET}
            x2={circuitWidth + 60}
            y2={20 + i * CELL_HEIGHT + WIRE_Y_OFFSET}
            stroke={WIRE_COLOR}
            strokeWidth={1.5}
          />
        ))}

        {/* Operations */}
        {operations.map((op, opIndex) => {
          const x = 80 + opIndex * CELL_WIDTH;
          const isCurrentStep = executionState === 'running' && opIndex === currentStep;

          if (op.type === 'gate' && op.gate) {
            const info = GATE_INFO[op.gate.gate_name];
            const fam = GATE_FAMILIES[info?.family ?? 'pauli'];
            const qubits = op.gate.qubits;

            if (qubits.length === 1) {
              const y = 20 + qubits[0] * CELL_HEIGHT + WIRE_Y_OFFSET;
              return (
                <g
                  key={`op-${opIndex}`}
                  className="cursor-pointer"
                  onClick={() => removeOperation(opIndex)}
                >
                  {isCurrentStep && (
                    <rect
                      x={x - 24}
                      y={y - 24}
                      width={48}
                      height={48}
                      fill="none"
                      stroke="#0f62fe"
                      strokeWidth={2}
                      rx={2}
                    />
                  )}
                  <rect
                    x={x - 20}
                    y={y - 20}
                    width={40}
                    height={40}
                    rx={2}
                    fill={fam.fill}
                  />
                  <text
                    x={x}
                    y={y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill={fam.text}
                    className="text-xs font-semibold pointer-events-none"
                    style={{ fontFamily: "'IBM Plex Mono', monospace" }}
                  >
                    {info?.symbol || op.gate.gate_name}
                  </text>
                  {op.gate.params.length > 0 && (
                    <text
                      x={x}
                      y={y + 28}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="#8d8d8d"
                      className="text-[9px] pointer-events-none"
                      style={{ fontFamily: "'IBM Plex Mono', monospace" }}
                    >
                      {(op.gate.params[0] / Math.PI).toFixed(1)}π
                    </text>
                  )}
                </g>
              );
            } else if (qubits.length === 2) {
              const y1 = 20 + qubits[0] * CELL_HEIGHT + WIRE_Y_OFFSET;
              const y2 = 20 + qubits[1] * CELL_HEIGHT + WIRE_Y_OFFSET;
              const minY = Math.min(y1, y2);
              const maxY = Math.max(y1, y2);
              const isCNOT = ['CX', 'CY', 'CZ'].includes(op.gate.gate_name);

              return (
                <g
                  key={`op-${opIndex}`}
                  className="cursor-pointer"
                  onClick={() => removeOperation(opIndex)}
                >
                  <line
                    x1={x}
                    y1={minY}
                    x2={x}
                    y2={maxY}
                    stroke="#161616"
                    strokeWidth={1.5}
                  />

                  {isCNOT ? (
                    <>
                      {/* Control dot — solid black */}
                      <circle cx={x} cy={y1} r={5} fill="#161616" />
                      {/* Target — black circle-plus */}
                      <circle
                        cx={x}
                        cy={y2}
                        r={15}
                        fill="#ffffff"
                        stroke="#161616"
                        strokeWidth={1.5}
                      />
                      <line x1={x - 15} y1={y2} x2={x + 15} y2={y2} stroke="#161616" strokeWidth={1.5} />
                      <line x1={x} y1={y2 - 15} x2={x} y2={y2 + 15} stroke="#161616" strokeWidth={1.5} />
                    </>
                  ) : (
                    <>
                      <rect
                        x={x - 20}
                        y={y1 - 20}
                        width={40}
                        height={40}
                        rx={2}
                        fill={fam.fill}
                      />
                      <rect
                        x={x - 20}
                        y={y2 - 20}
                        width={40}
                        height={40}
                        rx={2}
                        fill={fam.fill}
                      />
                      <text
                        x={x}
                        y={(y1 + y2) / 2}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="#161616"
                        className="text-xs font-semibold pointer-events-none"
                        style={{ fontFamily: "'IBM Plex Mono', monospace" }}
                      >
                        {info?.symbol || op.gate.gate_name}
                      </text>
                    </>
                  )}
                </g>
              );
            } else if (qubits.length === 3) {
              const ys = qubits.map(q => 20 + q * CELL_HEIGHT + WIRE_Y_OFFSET);
              const minY = Math.min(...ys);
              const maxY = Math.max(...ys);

              return (
                <g
                  key={`op-${opIndex}`}
                  className="cursor-pointer"
                  onClick={() => removeOperation(opIndex)}
                >
                  <line
                    x1={x}
                    y1={minY}
                    x2={x}
                    y2={maxY}
                    stroke="#161616"
                    strokeWidth={1.5}
                  />
                  <circle cx={x} cy={ys[0]} r={5} fill="#161616" />
                  <circle cx={x} cy={ys[1]} r={5} fill="#161616" />
                  <circle
                    cx={x}
                    cy={ys[2]}
                    r={15}
                    fill="#ffffff"
                    stroke="#161616"
                    strokeWidth={1.5}
                  />
                  <line x1={x - 15} y1={ys[2]} x2={x + 15} y2={ys[2]} stroke="#161616" strokeWidth={1.5} />
                  <line x1={x} y1={ys[2] - 15} x2={x} y2={ys[2] + 15} stroke="#161616" strokeWidth={1.5} />
                </g>
              );
            }
          } else if (op.type === 'measurement') {
            const qubits = op.measurement?.qubits || op.qubits;
            return qubits.map((q, idx) => {
              const y = 20 + q * CELL_HEIGHT + WIRE_Y_OFFSET;
              return (
                <g
                  key={`op-${opIndex}-m-${idx}`}
                  className="cursor-pointer"
                  onClick={() => removeOperation(opIndex)}
                >
                  <rect
                    x={x - 20}
                    y={y - 20}
                    width={40}
                    height={40}
                    rx={2}
                    fill={MEAS.fill}
                  />
                  <path
                    d={`M ${x - 10} ${y + 5} Q ${x} ${y - 15} ${x + 10} ${y + 5}`}
                    fill="none"
                    stroke={MEAS.text}
                    strokeWidth={1.5}
                  />
                  <line
                    x1={x}
                    y1={y - 5}
                    x2={x + 8}
                    y2={y - 12}
                    stroke={MEAS.text}
                    strokeWidth={1.5}
                  />
                </g>
              );
            });
          } else if (op.type === 'barrier') {
            const qubits = op.qubits;
            const minQ = Math.min(...qubits);
            const maxQ = Math.max(...qubits);
            const y1 = 20 + minQ * CELL_HEIGHT + WIRE_Y_OFFSET - 25;
            const y2 = 20 + maxQ * CELL_HEIGHT + WIRE_Y_OFFSET + 25;

            return (
              <g
                key={`op-${opIndex}`}
                className="cursor-pointer"
                onClick={() => removeOperation(opIndex)}
              >
                <line
                  x1={x}
                  y1={y1}
                  x2={x}
                  y2={y2}
                  stroke="#8d8d8d"
                  strokeWidth={1.5}
                  strokeDasharray="4,4"
                />
              </g>
            );
          }

          return null;
        })}

        {/* Empty state */}
        {operations.length === 0 && dropTarget === null && (
          <text
            x={circuitWidth / 2 + 60}
            y={(nQubits * CELL_HEIGHT) / 2 + 20}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#8d8d8d"
            className="text-xs"
            style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
          >
            Drag gates here
          </text>
        )}
      </svg>
    </div>
  );
}
