# Contributing

Contributions are welcome! This project is a quantum circuit simulator built for education and research.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/quantum-sim.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `cd backend && python -m pytest tests/ -v`
6. Commit with a descriptive message
7. Push and open a pull request

## Development Setup

### Backend
```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest tests/ -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Code Style

- **Python**: Follow PEP 8. Use type hints. Run `ruff check` before committing.
- **TypeScript**: Strict mode. No `any` types unless unavoidable.
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) format.

## Areas for Contribution

- Additional quantum algorithms (Shor's, quantum walks, etc.)
- More error correcting codes (surface codes, color codes)
- Performance optimizations (sparse matrices, GPU acceleration)
- Frontend visualizations (density matrix heatmap, Wigner function)
- Documentation and tutorials
- Additional test coverage

## Research Implementations

If implementing a research paper, please:
1. Add the full citation in the module docstring
2. Include arXiv links
3. Add the paper to the QSVT/Research panel if applicable
4. Write tests that verify the implementation against known results

## Reporting Issues

Use GitHub Issues. Include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python/Node version and OS
