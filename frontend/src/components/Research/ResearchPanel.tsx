import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { getQSVTDemo, type QSVTDemoResponse } from '../../api/client';

export function ResearchPanel() {
  const [result, setResult] = useState<QSVTDemoResponse | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: getQSVTDemo,
    onSuccess: setResult,
  });

  const toggle = (section: string) =>
    setExpandedSection(expandedSection === section ? null : section);

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-line px-4 py-3">
        <div className="text-sm font-semibold">Research implementation</div>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-3 text-xs">
        {/* Primary paper citation */}
        <div className="panel p-3 space-y-2">
          <div className="field-label">Based on</div>
          <div className="text-[12px] leading-relaxed font-medium">
            A. Gilyén, Y. Su, G. H. Low, N. Wiebe
          </div>
          <div className="text-[12px] text-gray-70 leading-relaxed italic">
            "Quantum Singular Value Transformations and Beyond:
            Exponential Improvements for Quantum Matrix Arithmetics"
          </div>
          <div className="flex gap-2 flex-wrap items-center">
            <span className="text-[11px] border border-line text-gray-70 px-2 py-0.5 rounded-[2px]">
              STOC 2019
            </span>
            <a href="https://arxiv.org/abs/1806.01838" target="_blank" rel="noopener noreferrer"
              className="text-[11px] text-blue-60 hover:underline">
              arXiv:1806.01838
            </a>
          </div>
        </div>

        {/* Precursor paper */}
        <div className="panel p-3 space-y-1.5">
          <div className="field-label">Precursor</div>
          <div className="text-[11px] text-gray-70 leading-relaxed">
            G. H. Low, I. L. Chuang — <span className="italic">"Quantum Signal Processing
            by Single-Qubit Dynamics"</span>
          </div>
          <div className="flex gap-2 items-center">
            <span className="text-[11px] border border-line text-gray-70 px-2 py-0.5 rounded-[2px]">
              PRL 2017
            </span>
            <a href="https://arxiv.org/abs/1610.06546" target="_blank" rel="noopener noreferrer"
              className="text-[11px] text-blue-60 hover:underline">
              arXiv:1610.06546
            </a>
          </div>
        </div>

        {/* What is QSVT */}
        <div className="panel p-3">
          <div className="field-label mb-2">What is QSVT?</div>
          <div className="text-[11px] text-gray-70 leading-relaxed space-y-2">
            <p>
              QSVT is a <span className="text-gray-100 font-medium">unified framework</span> for quantum algorithms.
              It applies <span className="text-gray-100 font-medium">polynomial transformations</span> to the singular
              values of a block-encoded matrix using quantum signal processing.
            </p>
            <p>
              Given a matrix A embedded in a unitary U (block encoding), QSVT constructs
              a circuit that implements p(A), where p is any bounded polynomial — by
              interleaving U with single-qubit phase rotations.
            </p>
            <p className="text-gray-100 border-l-2 border-blue-60 bg-blue-10 p-2">
              Key insight: major quantum algorithms are all special cases of choosing
              different polynomials p.
            </p>
          </div>
        </div>

        {/* Run demo */}
        <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
          className="btn-primary w-full py-2.5">
          {mutation.isPending ? 'Computing…' : 'Run unification demo'}
        </button>

        {result && (
          <div className="space-y-2">
            <div className="field-label pt-1">
              Algorithms unified by QSVT
            </div>

            {([
              ['grover', "1. Grover's search", result.grover],
              ['qpe', '2. Phase estimation', result.phase_estimation],
              ['hhl', '3. HHL (linear systems)', result.hhl],
              ['ham', '4. Hamiltonian simulation', result.hamiltonian_sim],
            ] as const).map(([key, title, data]) => (
              <div key={key} className="panel overflow-hidden">
                <button onClick={() => toggle(key)}
                  className="w-full text-left px-3 py-2 flex justify-between items-center hover:bg-gray-10 transition-colors duration-[70ms]">
                  <span className="font-medium text-[12px]">{title}</span>
                  <span className="text-gray-50">{expandedSection === key ? '−' : '+'}</span>
                </button>
                {expandedSection === key && (
                  <div className="px-3 pb-3 space-y-1 text-[11px] text-gray-70 border-t border-line pt-2">
                    <div><span className="text-gray-100 font-medium">Polynomial:</span> {String(data.polynomial)}</div>
                    <div><span className="text-gray-100 font-medium">QSVT action:</span> {String(data.qsvt_action)}</div>
                    <div><span className="text-gray-100 font-medium">Equivalent to:</span> {String(data.classical_equivalent)}</div>
                    {'complexity' in data && data.complexity !== undefined ? (
                      <div><span className="text-gray-100 font-medium">Complexity:</span> {String(data.complexity)}</div>
                    ) : (
                      <div><span className="text-gray-100 font-medium">Advantage:</span> No QFT required</div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Framework summary */}
            <div className="panel border-l-2 !border-l-blue-60 p-3 mt-2">
              <div className="field-label mb-1">Key insight</div>
              <div className="text-[11px] text-gray-70 leading-relaxed">
                {result.framework.key_insight}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
