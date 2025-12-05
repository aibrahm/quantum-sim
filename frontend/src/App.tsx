import { useState } from 'react';
import { CircuitBuilder } from './components/CircuitBuilder/CircuitBuilder';
import { GatePalette } from './components/CircuitBuilder/GatePalette';
import { BlochSphere } from './components/Visualizations/BlochSphere';
import { Histogram } from './components/Visualizations/Histogram';
import { StateVector } from './components/Visualizations/StateVector';
import { ControlPanel } from './components/ControlPanel';
import { AlgorithmsPanel } from './components/Algorithms';
import { useCircuitStore } from './stores/circuitStore';

type RightPanelMode = 'visualize' | 'algorithms';

function App() {
  const [rightPanelMode, setRightPanelMode] = useState<RightPanelMode>('visualize');
  const [activeTab, setActiveTab] = useState<'histogram' | 'state' | 'bloch'>('histogram');
  const { nQubits, result } = useCircuitStore();

  return (
    <div className="min-h-screen bg-black text-white font-mono">
      {/* Header */}
      <header className="bg-black border-b border-white px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold uppercase tracking-wide">
              QUANTUM CIRCUIT SIM
            </h1>
            <span className="text-xs text-gray-400">
              [{nQubits}Q]
            </span>
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => setRightPanelMode('visualize')}
              className={`px-3 py-1 text-xs font-bold uppercase border ${
                rightPanelMode === 'visualize'
                  ? 'border-white bg-white text-black'
                  : 'border-gray-600 hover:border-white'
              }`}
            >
              VIS
            </button>
            <button
              onClick={() => setRightPanelMode('algorithms')}
              className={`px-3 py-1 text-xs font-bold uppercase border ${
                rightPanelMode === 'algorithms'
                  ? 'border-white bg-white text-black'
                  : 'border-gray-600 hover:border-white'
              }`}
            >
              ALGO
            </button>
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-49px)]">
        {/* Left sidebar - Gate Palette */}
        <aside className="w-56 bg-black border-r border-white overflow-y-auto">
          <GatePalette />
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Circuit Builder */}
          <div className="flex-1 overflow-auto p-4">
            <CircuitBuilder />
          </div>

          {/* Control Panel */}
          <div className="border-t border-white bg-black p-3">
            <ControlPanel />
          </div>
        </main>

        {/* Right sidebar */}
        <aside className="w-80 bg-black border-l border-white flex flex-col">
          {rightPanelMode === 'algorithms' ? (
            <AlgorithmsPanel />
          ) : (
            <>
              {/* Visualization tabs */}
              <div className="flex border-b border-white">
                <button
                  onClick={() => setActiveTab('histogram')}
                  className={`flex-1 px-3 py-2 text-xs font-bold uppercase ${
                    activeTab === 'histogram'
                      ? 'bg-white text-black'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  HIST
                </button>
                <button
                  onClick={() => setActiveTab('state')}
                  className={`flex-1 px-3 py-2 text-xs font-bold uppercase border-l border-white ${
                    activeTab === 'state'
                      ? 'bg-white text-black'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  STATE
                </button>
                <button
                  onClick={() => setActiveTab('bloch')}
                  className={`flex-1 px-3 py-2 text-xs font-bold uppercase border-l border-white ${
                    activeTab === 'bloch'
                      ? 'bg-white text-black'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  BLOCH
                </button>
              </div>

              {/* Visualization content */}
              <div className="flex-1 overflow-auto p-3">
                {activeTab === 'histogram' && <Histogram />}
                {activeTab === 'state' && <StateVector />}
                {activeTab === 'bloch' && <BlochSphere />}
              </div>

              {/* Results summary */}
              {result && (
                <div className="border-t border-white p-3">
                  <div className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                    RESULTS
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="border border-gray-600 p-2">
                      <div className="text-gray-500">SHOTS</div>
                      <div className="font-bold">{result.shots}</div>
                    </div>
                    <div className="border border-gray-600 p-2">
                      <div className="text-gray-500">TIME</div>
                      <div className="font-bold">
                        {result.execution_time_ms.toFixed(1)}ms
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
