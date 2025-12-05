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
      <div className="flex items-center justify-center h-64 text-gray-600 text-xs uppercase">
        NO DATA - RUN CIRCUIT
      </div>
    );
  }

  return (
    <div className="space-y-3 text-xs">
      <div className="text-gray-500 uppercase font-bold">
        {result ? 'MEASUREMENT' : 'PROBABILITY'}
      </div>

      <div className="space-y-1">
        {data.map(({ label, value, count }) => (
          <div key={label}>
            <div className="flex items-center gap-2">
              <span className="text-gray-500 w-16">|{label}⟩</span>
              <div className="flex-1 h-4 border border-gray-700 bg-black">
                <div
                  className="h-full bg-white"
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

      <div className="pt-2 border-t border-gray-700">
        <div className="flex justify-between text-gray-600">
          <span>STATES: {data.length}</span>
          <span>MAX: {(maxValue * 100).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}
