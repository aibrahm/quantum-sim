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
      <div className="border-b border-qborder px-3 py-2 bg-surface">
        <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500">RESEARCH IMPLEMENTATION</div>
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-3 text-xs">
        {/* Primary paper citation */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 space-y-2">
          <div className="text-accent uppercase font-bold text-[10px] tracking-wider">BASED ON</div>
          <div className="text-[11px] text-gray-800 leading-relaxed font-medium">
            A. Gilyén, Y. Su, G. H. Low, N. Wiebe
          </div>
          <div className="text-[11px] text-gray-700 leading-relaxed italic">
            "Quantum Singular Value Transformations and Beyond:
            Exponential Improvements for Quantum Matrix Arithmetics"
          </div>
          <div className="flex gap-2 flex-wrap">
            <span className="text-[9px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-bold">STOC 2019</span>
            <a href="https://arxiv.org/abs/1806.01838" target="_blank" rel="noopener noreferrer"
              className="text-[9px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-bold hover:bg-blue-200 transition-colors">
              arXiv:1806.01838
            </a>
          </div>
        </div>

        {/* Precursor paper */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 space-y-1">
          <div className="text-accent-purple uppercase font-bold text-[10px] tracking-wider">PRECURSOR</div>
          <div className="text-[10px] text-gray-700 leading-relaxed">
            G. H. Low, I. L. Chuang — <span className="italic">"Quantum Signal Processing
            by Single-Qubit Dynamics"</span>
          </div>
          <div className="flex gap-2">
            <span className="text-[9px] bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-bold">PRL 2017</span>
            <a href="https://arxiv.org/abs/1610.06546" target="_blank" rel="noopener noreferrer"
              className="text-[9px] bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-bold hover:bg-purple-200 transition-colors">
              arXiv:1610.06546
            </a>
          </div>
        </div>

        {/* What is QSVT */}
        <div className="panel p-3">
          <div className="text-gray-500 uppercase font-bold text-[10px] tracking-wider mb-2">WHAT IS QSVT?</div>
          <div className="text-[10px] text-gray-600 leading-relaxed space-y-2">
            <p>
              QSVT is a <span className="text-gray-900 font-bold">unified framework</span> for quantum algorithms.
              It applies <span className="text-gray-900 font-bold">polynomial transformations</span> to the singular
              values of a block-encoded matrix using quantum signal processing.
            </p>
            <p>
              Given a matrix A embedded in a unitary U (block encoding), QSVT constructs
              a circuit that implements p(A), where p is any bounded polynomial — by
              interleaving U with single-qubit phase rotations.
            </p>
            <p className="text-gray-900 font-medium bg-yellow-50 border border-yellow-200 rounded p-2">
              Key insight: major quantum algorithms are all special cases of choosing
              different polynomials p.
            </p>
          </div>
        </div>

        {/* Run demo */}
        <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
          className="w-full py-2.5 btn-accent rounded-md text-[10px] tracking-wider">
          {mutation.isPending ? 'COMPUTING...' : 'RUN UNIFICATION DEMO'}
        </button>

        {result && (
          <div className="space-y-2">
            <div className="text-gray-500 uppercase font-bold text-[10px] tracking-wider pt-1">
              ALGORITHMS UNIFIED BY QSVT
            </div>

            {/* Grover */}
            <div className="panel overflow-hidden">
              <button onClick={() => toggle('grover')}
                className="w-full text-left px-3 py-2 flex justify-between items-center hover:bg-gray-50 transition-colors">
                <span className="font-bold text-gray-800">1. GROVER'S SEARCH</span>
                <span className="text-gray-400">{expandedSection === 'grover' ? '−' : '+'}</span>
              </button>
              {expandedSection === 'grover' && (
                <div className="px-3 pb-3 space-y-1 text-[10px] text-gray-600 border-t border-gray-100 pt-2">
                  <div><span className="text-gray-400 font-bold">Polynomial:</span> {result.grover.polynomial}</div>
                  <div><span className="text-gray-400 font-bold">QSVT action:</span> {result.grover.qsvt_action}</div>
                  <div><span className="text-gray-400 font-bold">Equivalent to:</span> {result.grover.classical_equivalent}</div>
                  <div><span className="text-gray-400 font-bold">Complexity:</span> {result.grover.complexity}</div>
                </div>
              )}
            </div>

            {/* Phase Estimation */}
            <div className="panel overflow-hidden">
              <button onClick={() => toggle('qpe')}
                className="w-full text-left px-3 py-2 flex justify-between items-center hover:bg-gray-50 transition-colors">
                <span className="font-bold text-gray-800">2. PHASE ESTIMATION</span>
                <span className="text-gray-400">{expandedSection === 'qpe' ? '−' : '+'}</span>
              </button>
              {expandedSection === 'qpe' && (
                <div className="px-3 pb-3 space-y-1 text-[10px] text-gray-600 border-t border-gray-100 pt-2">
                  <div><span className="text-gray-400 font-bold">Polynomial:</span> {result.phase_estimation.polynomial}</div>
                  <div><span className="text-gray-400 font-bold">QSVT action:</span> {result.phase_estimation.qsvt_action}</div>
                  <div><span className="text-gray-400 font-bold">Equivalent to:</span> {result.phase_estimation.classical_equivalent}</div>
                  <div><span className="text-gray-400 font-bold">Advantage:</span> No QFT required</div>
                </div>
              )}
            </div>

            {/* HHL */}
            <div className="panel overflow-hidden">
              <button onClick={() => toggle('hhl')}
                className="w-full text-left px-3 py-2 flex justify-between items-center hover:bg-gray-50 transition-colors">
                <span className="font-bold text-gray-800">3. HHL (LINEAR SYSTEMS)</span>
                <span className="text-gray-400">{expandedSection === 'hhl' ? '−' : '+'}</span>
              </button>
              {expandedSection === 'hhl' && (
                <div className="px-3 pb-3 space-y-1 text-[10px] text-gray-600 border-t border-gray-100 pt-2">
                  <div><span className="text-gray-400 font-bold">Polynomial:</span> {String(result.hhl.polynomial)}</div>
                  <div><span className="text-gray-400 font-bold">QSVT action:</span> {String(result.hhl.qsvt_action)}</div>
                  <div><span className="text-gray-400 font-bold">Equivalent to:</span> {String(result.hhl.classical_equivalent)}</div>
                  <div><span className="text-gray-400 font-bold">Complexity:</span> {String(result.hhl.complexity)}</div>
                </div>
              )}
            </div>

            {/* Hamiltonian Simulation */}
            <div className="panel overflow-hidden">
              <button onClick={() => toggle('ham')}
                className="w-full text-left px-3 py-2 flex justify-between items-center hover:bg-gray-50 transition-colors">
                <span className="font-bold text-gray-800">4. HAMILTONIAN SIMULATION</span>
                <span className="text-gray-400">{expandedSection === 'ham' ? '−' : '+'}</span>
              </button>
              {expandedSection === 'ham' && (
                <div className="px-3 pb-3 space-y-1 text-[10px] text-gray-600 border-t border-gray-100 pt-2">
                  <div><span className="text-gray-400 font-bold">Polynomial:</span> {String(result.hamiltonian_sim.polynomial)}</div>
                  <div><span className="text-gray-400 font-bold">QSVT action:</span> {String(result.hamiltonian_sim.qsvt_action)}</div>
                  <div><span className="text-gray-400 font-bold">Equivalent to:</span> {String(result.hamiltonian_sim.classical_equivalent)}</div>
                  <div><span className="text-gray-400 font-bold">Complexity:</span> {String(result.hamiltonian_sim.complexity)}</div>
                </div>
              )}
            </div>

            {/* Framework summary */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 mt-2">
              <div className="text-green-700 uppercase font-bold text-[10px] tracking-wider mb-1">KEY INSIGHT</div>
              <div className="text-[10px] text-green-800 leading-relaxed">
                {result.framework.key_insight}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
