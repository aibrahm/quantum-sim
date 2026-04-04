import { useMemo } from 'react';
import { useCircuitStore } from '../../stores/circuitStore';

export function Histogram() {
  const { result, nQubits, probabilities } = useCircuitStore();

  const data = useMemo(() => {
    if (result) {
      const entries = Object.entries(result.counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 16);

      const total = result.shots;
      return entries.map(([label, count]) => ({
        label,
        value: count / total,
        count,
      }));
    }

    const entries: { label: string; value: number; count: number }[] = [];
    for (let i = 0; i < probabilities.length; i++) {
      if (probabilities[i] > 0.001) {
        entries.push({
          label: i.toString(2).padStart(nQubits, '0'),
          value: probabilities[i],
          count: 0,
        });
      }
    }

    return entries.sort((a, b) => b.value - a.value).slice(0, 16);
  }, [result, probabilities, nQubits]);

  const maxValue = Math.max(...data.map(d => d.value), 0.01);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-600 text-xs uppercase tracking-wider">
        NO DATA — RUN CIRCUIT
      </div>
    );
  }

  return (
    <div className="space-y-3 text-xs">
      <div className="text-gray-400 uppercase font-bold text-[10px] tracking-wider">
        {result ? 'MEASUREMENT' : 'PROBABILITY'}
      </div>

      <div className="space-y-1">
        {data.map(({ label, value, count }) => (
          <div key={label}>
            <div className="flex items-center gap-2">
              <span className="text-accent font-bold w-16">|{label}⟩</span>
              <div className="flex-1 h-5 border border-qborder bg-gray-50 rounded overflow-hidden">
                <div
                  className="h-full bar-fill rounded-sm"
                  style={{ width: `${(value / maxValue) * 100}%` }}
                />
              </div>
              <span className="w-14 text-right text-gray-400">
                {(value * 100).toFixed(1)}%
              </span>
            </div>
            {result && (
              <div className="text-gray-600 ml-[72px]">
                {count}/{result.shots}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-qborder">
        <div className="flex justify-between text-gray-600">
          <span>STATES: {data.length}</span>
          <span>MAX: {(maxValue * 100).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}
