import { useMemo } from 'react';
import { useCircuitStore } from '../../stores/circuitStore';

/** Small plain phase gauge: 1px ring, needle at the complex phase angle. */
function PhaseDial({ phase }: { phase: number }) {
  const r = 7;
  const cx = 9;
  const cy = 9;
  // SVG y grows downward — negate the angle so positive phase reads CCW.
  const nx = cx + r * Math.cos(-phase);
  const ny = cy + r * Math.sin(-phase);
  return (
    <svg width={18} height={18} className="shrink-0" aria-hidden>
      <circle cx={cx} cy={cy} r={r + 1} fill="none" stroke="#c6c6c6" strokeWidth={1} />
      {/* 0-phase tick */}
      <line x1={cx + r - 1} y1={cy} x2={cx + r + 2} y2={cy} stroke="#8d8d8d" strokeWidth={1} />
      <line
        x1={cx}
        y1={cy}
        x2={nx}
        y2={ny}
        stroke="#161616"
        strokeWidth={1.5}
        style={{ transition: 'all 70ms ease' }}
      />
      <circle cx={cx} cy={cy} r={1.5} fill="#161616" />
    </svg>
  );
}

export function StateVector() {
  const { nQubits, probabilities, amplitudesReal, amplitudesImag } = useCircuitStore();

  const amplitudes = useMemo(() => {
    const hasComplex = amplitudesReal.length === probabilities.length;
    return probabilities.map((p, i) => {
      const re = hasComplex ? amplitudesReal[i] : Math.sqrt(p);
      const im = hasComplex ? amplitudesImag[i] : 0;
      return {
        index: i,
        label: i.toString(2).padStart(nQubits, '0'),
        magnitude: hasComplex ? Math.hypot(re, im) : Math.sqrt(p),
        probability: p,
        phase: hasComplex ? Math.atan2(im, re) : 0,
      };
    });
  }, [probabilities, amplitudesReal, amplitudesImag, nQubits]);

  const nonZeroAmps = amplitudes.filter(a => a.magnitude > 0.001);
  const maxMag = Math.max(...amplitudes.map(a => a.magnitude), 0.01);

  return (
    <div className="space-y-3 text-xs">
      <div className="text-[13px] font-semibold">State vector</div>

      {nonZeroAmps.length === 0 ? (
        <div className="flex items-center justify-center h-32 text-gray-50 font-mono tabular-nums">
          |0...0⟩
        </div>
      ) : (
        <div className="space-y-2">
          {nonZeroAmps.slice(0, 16).map(({ label, magnitude, probability, phase }) => (
            <div key={label} className="space-y-0.5">
              <div className="flex items-center gap-2">
                <span className="font-mono w-14 tabular-nums">
                  |{label}⟩
                </span>
                <div className="flex-1 h-4 bar-track">
                  <div
                    className="h-full bar-fill-gray"
                    style={{ width: `${(magnitude / maxMag) * 100}%` }}
                  />
                </div>
                <span className="w-14 text-right text-gray-70 font-mono tabular-nums">
                  {magnitude.toFixed(3)}
                </span>
              </div>

              <div className="ml-[60px] flex items-center gap-3 text-gray-50 text-[11px] font-mono tabular-nums">
                <span>|α|²={probability.toFixed(4)}</span>
                <span className="flex items-center gap-1">
                  <PhaseDial phase={phase} />
                  φ={((phase * 180) / Math.PI).toFixed(0)}°
                </span>
              </div>
            </div>
          ))}

          {nonZeroAmps.length > 16 && (
            <div className="text-gray-50 text-center text-[11px]">
              +{nonZeroAmps.length - 16} more
            </div>
          )}
        </div>
      )}

      <div className="pt-2 border-t border-line space-y-1 text-[11px] font-mono tabular-nums">
        <div className="flex justify-between text-gray-50">
          <span>Dimension</span>
          <span className="text-gray-70">2^{nQubits}={Math.pow(2, nQubits)}</span>
        </div>
        <div className="flex justify-between text-gray-50">
          <span>Non-zero</span>
          <span className="text-gray-70">{nonZeroAmps.length}</span>
        </div>
        <div className="flex justify-between text-gray-50">
          <span>Norm</span>
          <span className="text-gray-100">{probabilities.reduce((sum, p) => sum + p, 0).toFixed(6)}</span>
        </div>
      </div>

      {nonZeroAmps.length > 0 && nonZeroAmps.length <= 4 && (
        <div className="pt-2 text-center stat p-2 font-mono tabular-nums text-gray-70">
          |ψ⟩ ={' '}
          {nonZeroAmps.map((a, i) => (
            <span key={a.label}>
              {i > 0 && ' + '}
              <span className="text-gray-100">{a.magnitude.toFixed(2)}</span>|{a.label}⟩
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
