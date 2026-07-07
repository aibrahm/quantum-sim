import { useMutation } from '@tanstack/react-query';
import { useCircuitStore } from '../stores/circuitStore';
import { createCircuit, runCircuit, exportOpenQASM, getStateVector } from '../api/client';

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
    setAmplitudes,
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

      // Fetch exact amplitudes so the State view can show real phase.
      let stateVector = null;
      if (mode === 'statevector') {
        try {
          stateVector = await getStateVector(circuit.id);
        } catch {
          stateVector = null;
        }
      }

      return { result, stateVector };
    },
    onSuccess: ({ result, stateVector }) => {
      setResult(result);

      if (stateVector) {
        setAmplitudes(stateVector.amplitudes_real, stateVector.amplitudes_imag);
        setProbabilities(stateVector.probabilities);
        setBlochVectors(stateVector.bloch_vectors);
      } else if (result.snapshots.length > 0) {
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
          className="btn-primary px-6 py-2"
        >
          {runMutation.isPending ? 'Running…' : 'Run'}
        </button>

        <button
          onClick={handleReset}
          className="btn-secondary px-3 py-2"
          title="Reset"
        >
          Reset
        </button>

        <button
          onClick={handleClear}
          className="btn-danger px-3 py-2"
          title="Clear"
        >
          Clear
        </button>
      </div>

      {/* Center: Settings */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="field-label">Shots</span>
          <select
            value={shots}
            onChange={(e) => setShots(parseInt(e.target.value))}
            className="px-2 py-1 text-[12px]"
          >
            <option value={100}>100</option>
            <option value={1024}>1024</option>
            <option value={4096}>4096</option>
            <option value={10000}>10000</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="field-label">Mode</span>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as 'statevector' | 'density_matrix')}
            className="px-2 py-1 text-[12px]"
          >
            <option value="statevector">State vector</option>
            <option value="density_matrix">Density matrix</option>
          </select>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={recordSnapshots}
            onChange={(e) => setRecordSnapshots(e.target.checked)}
            className="w-3 h-3"
          />
          <span className="field-label">Snapshots</span>
        </label>
      </div>

      {/* Right: Export + op counter */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => exportMutation.mutate()}
          disabled={exportMutation.isPending || operations.length === 0}
          className="btn-secondary px-3 py-2"
        >
          QASM
        </button>

        <span className="text-gray-70 font-mono tabular-nums">
          {operations.length} op{operations.length === 1 ? '' : 's'}
        </span>
      </div>
    </div>
  );
}
