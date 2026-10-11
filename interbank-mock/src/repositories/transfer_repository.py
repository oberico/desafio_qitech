import threading
import uuid


class TransferRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._transfer_ids = {}
        self._flaky_calls = {}

    def get_or_create_transfer_id(self, payout_key: str) -> str:
        with self._lock:
            if payout_key not in self._transfer_ids:
                self._transfer_ids[payout_key] = str(uuid.uuid4())
            return self._transfer_ids[payout_key]

    def register_flaky_call(self, payout_key: str) -> int:
        with self._lock:
            self._flaky_calls[payout_key] = self._flaky_calls.get(payout_key, 0) + 1
            return self._flaky_calls[payout_key]


transfer_repository = TransferRepository()
