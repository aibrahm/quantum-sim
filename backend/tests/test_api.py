"""Tests for the FastAPI layer."""

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from quantum_simulator.api.main import app


class TestAPIEndpoints:
    """Test endpoints run correctly with simulation work offloaded to a thread."""

    def test_health(self):
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    def test_grover_endpoint_n4(self):
        """Grover over 4 qubits through the API should find the marked state."""
        with TestClient(app) as client:
            response = client.post("/api/algorithms/grover", json={
                "n_qubits": 4,
                "marked_states": [11],
            })
            assert response.status_code == 200
            data = response.json()
            assert data["success_probability"] > 0.9

    def test_circuit_create_and_run(self):
        """Create a Bell circuit, run it, and check the output distribution."""
        with TestClient(app) as client:
            create = client.post("/api/circuit", json={
                "n_qubits": 2,
                "name": "bell",
                "operations": [
                    {"type": "gate", "qubits": [0],
                     "gate": {"gate_name": "H", "qubits": [0], "params": []}},
                    {"type": "gate", "qubits": [0, 1],
                     "gate": {"gate_name": "CX", "qubits": [0, 1], "params": []}},
                    {"type": "measurement", "qubits": [0, 1],
                     "measurement": {"qubits": [0, 1], "classical_bits": [0, 1]}},
                ],
            })
            assert create.status_code == 200
            circuit_id = create.json()["id"]

            run = client.post(f"/api/circuit/{circuit_id}/run", json={"shots": 1000})
            assert run.status_code == 200
            counts = run.json()["counts"]
            assert set(counts.keys()) == {"00", "11"}
