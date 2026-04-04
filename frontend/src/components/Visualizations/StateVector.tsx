import { useMemo } from 'react';
import { useCircuitStore } from '../../stores/circuitStore';

export function StateVector() {
  const { nQubits, probabilities } = useCircuitStore();

  const amplitudes = useMemo(() => {
    return probabilities.map((p, i) => ({
      index: i,
      label: i.toString(2).padStart(nQubits, '0'),
      magnitude: Math.sqrt(p),
      probability: p,
      phase: 0,
    }));
  }, [probabilities, nQubits]);

  const nonZeroAmps = amplitudes.filter(a => a.magnitude > 0.001);
  const maxMag = Math.max(...amplitudes.map(a => a.magnitude), 0.01);

  return (
    <div className="space-y-3 text-xs">
      <div className="text-gray-400 uppercase font-bold text-[10px] tracking-wider">
        STATE VECTOR
      </div>

      {nonZeroAmps.length === 0 ? (
        <div className="flex items-center justify-center h-32 text-gray-600">
          |0...0⟩
        </div>
      ) : (
        <div className="space-y-2">
          {nonZeroAmps.slice(0, 16).map(({ label, magnitude, probability, phase }) => (
            <div key={label} className="space-y-0.5">
              <div className="flex items-center gap-2">
                <span className="text-accent font-bold w-14">
                  |{label}⟩
                </span>
                <div className="flex-1 h-5 border border-qborder bg-gray-50 rounded overflow-hidden">
                  <div
                    className="h-full bar-fill-cyan rounded-sm"
                    style={{ width: `${(magnitude / maxMag) * 100}%` }}
                  />
                </div>
                <span className="w-14 text-right text-gray-400">
                  {magnitude.toFixed(3)}
                </span>
              </div>

              <div className="ml-[60px] flex gap-4 text-gray-600">
                <span>|α|²={probability.toFixed(4)}</span>
                <span>φ={((phase * 180) / Math.PI).toFixed(0)}°</span>
              </div>
            </div>
          ))}

          {nonZeroAmps.length > 16 && (
            <div className="text-gray-600 text-center">
              +{nonZeroAmps.length - 16} MORE
            </div>
          )}
        </div>
      )}

      <div className="pt-2 border-t border-qborder space-y-1">
        <div className="flex justify-between text-gray-600">
          <span>DIM</span>
          <span>2^{nQubits}={Math.pow(2, nQubits)}</span>
        </div>
        <div className="flex justify-between text-gray-600">
          <span>NON-ZERO</span>
          <span>{nonZeroAmps.length}</span>
        </div>
        <div className="flex justify-between text-gray-600">
          <span>NORM</span>
          <span>{probabilities.reduce((sum, p) => sum + p, 0).toFixed(6)}</span>
        </div>
      </div>

      {nonZeroAmps.length > 0 && nonZeroAmps.length <= 4 && (
        <div className="pt-2 text-center text-gray-400">
          |ψ⟩ ={' '}
          {nonZeroAmps.map((a, i) => (
            <span key={a.label}>
              {i > 0 && ' + '}
              {a.magnitude.toFixed(2)}|{a.label}⟩
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
