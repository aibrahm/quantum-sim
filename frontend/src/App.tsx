import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CircuitBuilder } from './components/CircuitBuilder/CircuitBuilder';
import { GatePalette } from './components/CircuitBuilder/GatePalette';
import { BlochSphere } from './components/Visualizations/BlochSphere';
import { Histogram } from './components/Visualizations/Histogram';
import { StateVector } from './components/Visualizations/StateVector';
import { ControlPanel } from './components/ControlPanel';
import { StepControl } from './components/StepControl';
import { AlgorithmsPanel } from './components/Algorithms';
import { ResearchPanel } from './components/Research';
import { ToolsPanel } from './components/Tools';
import { useCircuitStore } from './stores/circuitStore';
import { healthCheck } from './api/client';

type RightPanelMode = 'visualize' | 'algorithms' | 'research' | 'tools';

function BackendStatus() {
  const { status } = useQuery({
    queryKey: ['health'],
    queryFn: healthCheck,
    refetchInterval: 15000,
    retry: false,
  });

  const state = status === 'success' ? 'ok' : status === 'error' ? 'err' : 'wait';

  return (
    <div className="flex items-center gap-2">
      <span className={`status-dot ${state}`} />
      <span className="text-xs text-gray-70">
        {state === 'ok' ? 'Connected' : state === 'err' ? 'Offline' : 'Connecting'}
      </span>
    </div>
  );
}

function App() {
  const [rightPanelMode, setRightPanelMode] = useState<RightPanelMode>('visualize');
  const [activeTab, setActiveTab] = useState<'histogram' | 'state' | 'bloch'>('histogram');
  const { nQubits, result } = useCircuitStore();

  return (
    <div className="min-h-screen font-sans text-gray-100">
      {/* Top bar */}
      <header className="bg-white px-4 h-12 border-b border-line flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 className="font-semibold text-sm leading-none">
            Quantum Circuit Simulator
          </h1>
          <span className="text-xs text-gray-50 font-mono tabular-nums">
            {nQubits} qubit{nQubits === 1 ? '' : 's'}
          </span>
        </div>

        <div className="flex items-center gap-6">
          {/* Mode tabs — Carbon text tabs, 2px blue underline */}
          <nav className="flex h-12">
            {([
              { id: 'visualize', label: 'Visualize' },
              { id: 'algorithms', label: 'Algorithms' },
              { id: 'research', label: 'QSVT' },
              { id: 'tools', label: 'Tools' },
            ] as const).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setRightPanelMode(tab.id)}
                className={`relative px-4 text-[13px] transition-colors duration-[70ms] ${
                  rightPanelMode === tab.id
                    ? 'text-gray-100 font-medium'
                    : 'text-gray-70 hover:text-gray-100'
                }`}
              >
                {tab.label}
                {rightPanelMode === tab.id && (
                  <span className="absolute inset-x-0 bottom-0 h-[2px] bg-blue-60" />
                )}
              </button>
            ))}
          </nav>

          {/* Backend status */}
          <BackendStatus />
        </div>
      </header>

      <div className="flex h-[calc(100vh-48px)]">
        {/* Left sidebar — gate palette */}
        <aside className="w-56 bg-white border-r border-line overflow-y-auto">
          <GatePalette />
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden bg-gray-10">
          {/* Circuit builder */}
          <div className="flex-1 overflow-auto p-4">
            <CircuitBuilder />
          </div>

          {/* Control deck */}
          <div className="border-t border-line bg-white px-4 py-3 space-y-3">
            <ControlPanel />
            <div className="border-t border-line pt-3">
              <StepControl />
            </div>
          </div>
        </main>

        {/* Right rail */}
        <aside className="w-80 bg-white border-l border-line flex flex-col">
          {rightPanelMode === 'algorithms' ? (
            <AlgorithmsPanel />
          ) : rightPanelMode === 'research' ? (
            <ResearchPanel />
          ) : rightPanelMode === 'tools' ? (
            <ToolsPanel />
          ) : (
            <>
              {/* Visualization tabs */}
              <div className="flex border-b border-line">
                {(['histogram', 'state', 'bloch'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`relative flex-1 px-3 py-2.5 text-[13px] transition-colors duration-[70ms] ${
                      activeTab === tab
                        ? 'text-gray-100 font-medium'
                        : 'text-gray-70 hover:text-gray-100'
                    }`}
                  >
                    {tab === 'histogram' ? 'Histogram' : tab === 'state' ? 'State' : 'Bloch'}
                    {activeTab === tab && (
                      <span className="absolute inset-x-0 bottom-0 h-[2px] bg-blue-60" />
                    )}
                  </button>
                ))}
              </div>

              {/* Visualization content */}
              <div className="flex-1 overflow-auto p-4">
                {activeTab === 'histogram' && <Histogram />}
                {activeTab === 'state' && <StateVector />}
                {activeTab === 'bloch' && <BlochSphere />}
              </div>

              {/* Results */}
              {result && (
                <div className="border-t border-line p-4">
                  <div className="field-label mb-2">Results</div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="stat p-2">
                      <div className="text-[11px] text-gray-50">Shots</div>
                      <div className="font-mono text-[13px] tabular-nums">{result.shots}</div>
                    </div>
                    <div className="stat p-2">
                      <div className="text-[11px] text-gray-50">Time</div>
                      <div className="font-mono text-[13px] tabular-nums">
                        {result.execution_time_ms.toFixed(1)}
                        <span className="text-gray-50 text-[11px] ml-0.5">ms</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;
