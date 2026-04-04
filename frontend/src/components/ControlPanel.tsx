import { useMutation } from '@tanstack/react-query';
import { useCircuitStore } from '../stores/circuitStore';
import { createCircuit, runCircuit, exportOpenQASM } from '../api/client';

export function ControlPanel() {
  const {
    nQubits,
    name,
    operations,
    shots,
    setShots,
    mode,
    setMode,
    recordSnapshots,
    setRecordSnapshots,
    circuitId,
    setCircuitId,
    setResult,
    setBlochVectors,
    setProbabilities,
    clearOperations,
    resetExecution,
    toOperationsPayload,
  } = useCircuitStore();

  const runMutation = useMutation({
    mutationFn: async () => {
      // Use toOperationsPayload to include initialization gates
      const circuit = await createCircuit(nQubits, name, toOperationsPayload());
      setCircuitId(circuit.id);

      const result = await runCircuit(circuit.id, {
        shots,
        mode,
        record_snapshots: recordSnapshots,
      });

      return result;
    },
    onSuccess: (result) => {
      setResult(result);

      if (result.snapshots.length > 0) {
        const lastSnapshot = result.snapshots[result.snapshots.length - 1];
        setBlochVectors(lastSnapshot.bloch_vectors);
        setProbabilities(lastSnapshot.probabilities);
      }
    },
    onError: (error) => {
      console.error('Error running circuit:', error);
      alert('ERROR: Check console');
    },
  });

  const exportMutation = useMutation({
    mutationFn: async () => {
      if (!circuitId) {
        const circuit = await createCircuit(nQubits, name, toOperationsPayload());
        setCircuitId(circuit.id);
        return exportOpenQASM(circuit.id);
      }
      return exportOpenQASM(circuitId);
    },
    onSuccess: (data) => {
      const blob = new Blob([data.qasm], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name}.qasm`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const handleRun = () => {
    runMutation.mutate();
  };

  const handleReset = () => {
    resetExecution();
    setCircuitId(null);
  };

  const handleClear = () => {
    clearOperations();
    resetExecution();
    setCircuitId(null);
  };

  return (
    <div className="flex items-center justify-between gap-4 text-xs">
      {/* Left: Run controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleRun}
          disabled={runMutation.isPending || operations.length === 0}
          className="px-5 py-2 btn-accent rounded text-[10px] tracking-widest"
        >
          {runMutation.isPending ? 'RUNNING...' : '▶ RUN'}
        </button>

        <button
          onClick={handleReset}
          className="px-3 py-2 border border-qborder hover:border-accent/50 hover:text-accent font-bold uppercase rounded transition-colors text-[10px]"
          title="Reset"
        >
          RST
        </button>

        <button
          onClick={handleClear}
          className="px-3 py-2 border border-qborder hover:border-red-500/50 hover:text-red-400 font-bold uppercase rounded transition-colors text-[10px]"
          title="Clear"
        >
          CLR
        </button>
      </div>

      {/* Center: Settings */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 uppercase text-[10px]">SHOTS</span>
          <select
            value={shots}
            onChange={(e) => setShots(parseInt(e.target.value))}
            className="bg-black border border-gray-600 px-2 py-1"
          >
            <option value={100}>100</option>
            <option value={1024}>1024</option>
            <option value={4096}>4096</option>
            <option value={10000}>10000</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-gray-500 uppercase text-[10px]">MODE</span>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as 'statevector' | 'density_matrix')}
            className="bg-black border border-gray-600 px-2 py-1"
          >
            <option value="statevector">SV</option>
            <option value="density_matrix">DM</option>
          </select>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={recordSnapshots}
            onChange={(e) => setRecordSnapshots(e.target.checked)}
            className="w-3 h-3"
          />
          <span className="text-gray-500 uppercase">SNAP</span>
        </label>
      </div>

      {/* Right: Export */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => exportMutation.mutate()}
          disabled={exportMutation.isPending || operations.length === 0}
          className="px-3 py-2 border border-qborder hover:border-accent-purple/50 hover:text-accent-purple disabled:border-qborder disabled:text-gray-600 font-bold uppercase rounded transition-colors text-[10px]"
        >
          QASM
        </button>

        <span className="text-gray-600">
          {operations.length} OPS
        </span>
      </div>
    </div>
  );
}
