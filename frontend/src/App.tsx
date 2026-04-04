import { useState } from 'react';
import { CircuitBuilder } from './components/CircuitBuilder/CircuitBuilder';
import { GatePalette } from './components/CircuitBuilder/GatePalette';
import { BlochSphere } from './components/Visualizations/BlochSphere';
import { Histogram } from './components/Visualizations/Histogram';
import { StateVector } from './components/Visualizations/StateVector';
import { ControlPanel } from './components/ControlPanel';
import { AlgorithmsPanel } from './components/Algorithms';
import { ResearchPanel } from './components/Research';
import { ToolsPanel } from './components/Tools';
import { useCircuitStore } from './stores/circuitStore';

type RightPanelMode = 'visualize' | 'algorithms' | 'research' | 'tools';

function App() {
  const [rightPanelMode, setRightPanelMode] = useState<RightPanelMode>('visualize');
  const [activeTab, setActiveTab] = useState<'histogram' | 'state' | 'bloch'>('histogram');
  const { nQubits, result } = useCircuitStore();

  return (
    <div className="min-h-screen bg-surface-2 text-gray-800 font-mono">
      {/* Accent stripe */}
      <div className="header-line" />

      {/* Header */}
      <header className="bg-white px-5 py-3 border-b border-qborder shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-base font-bold uppercase tracking-widest text-gray-900">
              <span className="text-accent">Q</span>UANTUM{' '}
              <span className="text-accent">C</span>IRCUIT{' '}
              <span className="text-accent">S</span>IMULATOR
            </h1>
            <span className="text-[10px] text-accent bg-blue-50 border border-accent/30 px-2 py-0.5 rounded-full font-bold">
              {nQubits} QUBIT{nQubits > 1 ? 'S' : ''}
            </span>
          </div>
          <div className="flex gap-1">
            {([
              { id: 'visualize', label: 'VIS' },
              { id: 'algorithms', label: 'ALGO' },
              { id: 'research', label: 'QSVT' },
              { id: 'tools', label: 'TOOLS' },
            ] as const).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setRightPanelMode(tab.id)}
                className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all duration-150 ${
                  rightPanelMode === tab.id
                    ? 'bg-gray-900 text-white shadow-md'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-51px)]">
        {/* Left sidebar - Gate Palette */}
        <aside className="w-56 bg-white border-r border-qborder overflow-y-auto shadow-sm">
          <GatePalette />
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Circuit Builder */}
          <div className="flex-1 overflow-auto p-4 bg-surface-2">
            <CircuitBuilder />
          </div>

          {/* Control Panel */}
          <div className="border-t border-qborder bg-white p-3 shadow-[0_-2px_8px_rgba(0,0,0,0.04)]">
            <ControlPanel />
          </div>
        </main>

        {/* Right sidebar */}
        <aside className="w-80 bg-white border-l border-qborder flex flex-col shadow-sm">
          {rightPanelMode === 'algorithms' ? (
            <AlgorithmsPanel />
          ) : rightPanelMode === 'research' ? (
            <ResearchPanel />
          ) : rightPanelMode === 'tools' ? (
            <ToolsPanel />
          ) : (
            <>
              {/* Visualization tabs */}
              <div className="flex border-b border-qborder bg-surface">
                {(['histogram', 'state', 'bloch'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`flex-1 px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider transition-all duration-150 ${
                      activeTab === tab
                        ? 'bg-accent text-white'
                        : 'text-gray-400 hover:text-accent hover:bg-blue-50'
                    }`}
                  >
                    {tab === 'histogram' ? 'HIST' : tab === 'state' ? 'STATE' : 'BLOCH'}
                  </button>
                ))}
              </div>

              {/* Visualization content */}
              <div className="flex-1 overflow-auto p-3">
                {activeTab === 'histogram' && <Histogram />}
                {activeTab === 'state' && <StateVector />}
                {activeTab === 'bloch' && <BlochSphere />}
              </div>

              {/* Results summary */}
              {result && (
                <div className="border-t border-qborder p-3 bg-surface">
                  <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-2 font-bold">
                    RESULTS
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="panel p-2">
                      <div className="text-gray-400 text-[10px]">SHOTS</div>
                      <div className="font-bold text-gray-800">{result.shots}</div>
                    </div>
                    <div className="panel p-2">
                      <div className="text-gray-400 text-[10px]">TIME</div>
                      <div className="font-bold text-accent">{result.execution_time_ms.toFixed(1)}ms</div>
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
