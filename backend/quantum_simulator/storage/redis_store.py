"""
Redis storage layer for circuit persistence.
"""

import json
import uuid
from typing import Optional, Dict, Any, List

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from ..circuit.circuit import QuantumCircuit


class CircuitStore:
    """
    Redis-based storage for quantum circuits and execution state.

    Stores:
    - Circuit definitions
    - Execution state (current step, state vector/density matrix)
    - Results cache
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize the store.

        Args:
            redis_url: Redis connection URL
        """
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._local_cache: Dict[str, Any] = {}  # Fallback for no Redis

    async def connect(self) -> None:
        """Connect to Redis."""
        if redis is None:
            print("Warning: redis package not installed, using in-memory storage")
            return

        try:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
        except Exception as e:
            print(f"Warning: Could not connect to Redis ({e}), using in-memory storage")
            self._redis = None

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()

    def _circuit_key(self, circuit_id: str) -> str:
        return f"circuit:{circuit_id}"

    def _state_key(self, circuit_id: str) -> str:
        return f"state:{circuit_id}"

    def _result_key(self, circuit_id: str) -> str:
        return f"result:{circuit_id}"

    async def generate_id(self) -> str:
        """Generate a unique circuit ID."""
        return str(uuid.uuid4())[:8]

    async def save_circuit(
        self,
        circuit_id: str,
        circuit: QuantumCircuit,
        ttl: int = 3600
    ) -> None:
        """
        Save a circuit.

        Args:
            circuit_id: Unique circuit identifier
            circuit: QuantumCircuit to save
            ttl: Time-to-live in seconds (default 1 hour)
        """
        data = json.dumps(circuit.to_dict())

        if self._redis:
            await self._redis.setex(self._circuit_key(circuit_id), ttl, data)
        else:
            self._local_cache[self._circuit_key(circuit_id)] = {
                'data': data,
                'ttl': ttl
            }

    async def get_circuit(self, circuit_id: str) -> Optional[QuantumCircuit]:
        """
        Retrieve a circuit.

        Args:
            circuit_id: Circuit identifier

        Returns:
            QuantumCircuit or None if not found
        """
        if self._redis:
            data = await self._redis.get(self._circuit_key(circuit_id))
        else:
            cached = self._local_cache.get(self._circuit_key(circuit_id))
            data = cached['data'] if cached else None

        if data is None:
            return None

        return QuantumCircuit.from_dict(json.loads(data))

    async def delete_circuit(self, circuit_id: str) -> bool:
        """
        Delete a circuit and its associated state.

        Args:
            circuit_id: Circuit identifier

        Returns:
            True if deleted, False if not found
        """
        keys = [
            self._circuit_key(circuit_id),
            self._state_key(circuit_id),
            self._result_key(circuit_id)
        ]

        if self._redis:
            deleted = await self._redis.delete(*keys)
            return deleted > 0
        else:
            deleted = False
            for key in keys:
                if key in self._local_cache:
                    del self._local_cache[key]
                    deleted = True
            return deleted

    async def save_state(
        self,
        circuit_id: str,
        state_data: Dict[str, Any],
        ttl: int = 3600
    ) -> None:
        """
        Save execution state.

        Args:
            circuit_id: Circuit identifier
            state_data: State dictionary (amplitudes, step, etc.)
            ttl: Time-to-live
        """
        data = json.dumps(state_data, default=self._json_encoder)

        if self._redis:
            await self._redis.setex(self._state_key(circuit_id), ttl, data)
        else:
            self._local_cache[self._state_key(circuit_id)] = {
                'data': data,
                'ttl': ttl
            }

    async def get_state(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve execution state.

        Args:
            circuit_id: Circuit identifier

        Returns:
            State dictionary or None
        """
        if self._redis:
            data = await self._redis.get(self._state_key(circuit_id))
        else:
            cached = self._local_cache.get(self._state_key(circuit_id))
            data = cached['data'] if cached else None

        if data is None:
            return None

        return json.loads(data)

    async def save_result(
        self,
        circuit_id: str,
        result_data: Dict[str, Any],
        ttl: int = 3600
    ) -> None:
        """
        Save execution result.

        Args:
            circuit_id: Circuit identifier
            result_data: Result dictionary
            ttl: Time-to-live
        """
        data = json.dumps(result_data, default=self._json_encoder)

        if self._redis:
            await self._redis.setex(self._result_key(circuit_id), ttl, data)
        else:
            self._local_cache[self._result_key(circuit_id)] = {
                'data': data,
                'ttl': ttl
            }

    async def get_result(self, circuit_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached execution result.

        Args:
            circuit_id: Circuit identifier

        Returns:
            Result dictionary or None
        """
        if self._redis:
            data = await self._redis.get(self._result_key(circuit_id))
        else:
            cached = self._local_cache.get(self._result_key(circuit_id))
            data = cached['data'] if cached else None

        if data is None:
            return None

        return json.loads(data)

    async def list_circuits(self, pattern: str = "*") -> List[str]:
        """
        List all circuit IDs.

        Args:
            pattern: Optional pattern to match

        Returns:
            List of circuit IDs
        """
        if self._redis:
            keys = await self._redis.keys(f"circuit:{pattern}")
            return [k.split(':')[1] for k in keys]
        else:
            return [
                k.split(':')[1] for k in self._local_cache.keys()
                if k.startswith('circuit:')
            ]

    async def extend_ttl(self, circuit_id: str, ttl: int = 3600) -> bool:
        """
        Extend TTL for a circuit and its state.

        Args:
            circuit_id: Circuit identifier
            ttl: New TTL in seconds

        Returns:
            True if successful
        """
        if self._redis:
            circuit_key = self._circuit_key(circuit_id)
            state_key = self._state_key(circuit_id)

            pipe = self._redis.pipeline()
            pipe.expire(circuit_key, ttl)
            pipe.expire(state_key, ttl)
            results = await pipe.execute()
            return all(results)

        return True  # No-op for local cache

    @staticmethod
    def _json_encoder(obj):
        """Custom JSON encoder for numpy arrays."""
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, complex):
            return {'real': obj.real, 'imag': obj.imag}
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# Global store instance
_store: Optional[CircuitStore] = None


async def get_store() -> CircuitStore:
    """Get the global circuit store instance."""
    global _store
    if _store is None:
        import os
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        _store = CircuitStore(redis_url)
        await _store.connect()
    return _store


async def close_store() -> None:
    """Close the global store connection."""
    global _store
    if _store:
        await _store.disconnect()
        _store = None
