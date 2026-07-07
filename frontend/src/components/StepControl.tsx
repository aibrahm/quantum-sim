import { useRef, useState, useCallback, useEffect } from 'react';
import { useCircuitStore } from '../stores/circuitStore';
import { createCircuit, createExecutionWebSocket } from '../api/client';
import type { BlochVector } from '../types';

interface StepMessage {
  type: 'init' | 'step' | 'complete' | 'reset';
  step?: number;
  operation?: string;
  qubits?: number[];
  probabilities?: number[];
  amplitudes_real?: number[] | null;
  amplitudes_imag?: number[] | null;
  bloch_vectors?: BlochVector[];
  total_steps?: number;
  message?: string;
}

export function StepControl() {
  const {
    nQubits,
    name,
    operations,
    toOperationsPayload,
    setProbabilities,
    setBlochVectors,
    setAmplitudes,
    setCurrentStep,
    resetExecution,
  } = useCircuitStore();

  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [step, setStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(0);
  const [done, setDone] = useState(false);

  const applyMessage = useCallback((data: StepMessage) => {
    if (data.type === 'init') {
      setTotalSteps(data.total_steps ?? 0);
      return;
    }
    if (data.type === 'complete') {
      setDone(true);
      return;
    }
    if (data.type === 'reset') {
      setStep(0);
      setDone(false);
      resetExecution();
      return;
    }
    if (data.type === 'step') {
      if (data.probabilities) setProbabilities(data.probabilities);
      if (data.bloch_vectors) setBlochVectors(data.bloch_vectors);
      if (data.amplitudes_real && data.amplitudes_imag) {
        setAmplitudes(data.amplitudes_real, data.amplitudes_imag);
      }
      if (typeof data.step === 'number') {
        setStep(data.step + 1);
        setCurrentStep(data.step);
      }
    }
  }, [setProbabilities, setBlochVectors, setAmplitudes, setCurrentStep, resetExecution]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  const connect = useCallback(async () => {
    // Persist the current circuit so the backend can address it by id.
    const circuit = await createCircuit(nQubits, name, toOperationsPayload());
    resetExecution();
    setStep(0);
    setDone(false);
    const ws = createExecutionWebSocket(
      circuit.id,
      (data) => applyMessage(data as StepMessage),
      () => setConnected(false),
      () => setConnected(false),
    );
    ws.onopen = () => setConnected(true);
    wsRef.current = ws;
  }, [nQubits, name, toOperationsPayload, resetExecution, applyMessage]);

  const send = useCallback((action: string) => {
    wsRef.current?.send(JSON.stringify({ action }));
  }, []);

  useEffect(() => disconnect, [disconnect]);

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="field-label mr-1">Step-through</span>

      {!connected ? (
        <button
          onClick={() => void connect()}
          disabled={operations.length === 0}
          className="btn-secondary px-3 py-2"
        >
          Connect
        </button>
      ) : (
        <>
          <button
            onClick={() => send('step')}
            disabled={done}
            className="btn-primary px-4 py-2"
          >
            Step
          </button>
          <button
            onClick={() => { setDone(false); send('run_all'); }}
            className="btn-secondary px-3 py-2"
          >
            Run all
          </button>
          <button
            onClick={() => send('reset')}
            className="btn-secondary px-3 py-2"
          >
            Reset
          </button>
          <button
            onClick={disconnect}
            className="btn-danger px-3 py-2"
          >
            Stop
          </button>
          <span className="text-gray-70 font-mono tabular-nums px-1">
            {step}/{totalSteps}
            {done && <span className="ml-1.5 text-green-50">done</span>}
          </span>
        </>
      )}
    </div>
  );
}
