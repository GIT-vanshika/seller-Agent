import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuditLogger:
    """
    Structured Audit Logger for security, compliance, policy evaluation, and deal consistency tracking.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / "audit.jsonl"
        self._in_memory_logs: List[Dict[str, Any]] = []

    def log_event(self, event_type: str, session_id: str, product_id: str, data: Dict[str, Any]):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "session_id": session_id,
            "product_id": product_id,
            "data": data,
        }
        self._in_memory_logs.append(record)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logging.error(f"Failed to write audit log event: {e}")

    def get_session_logs(self, session_id: str) -> List[Dict[str, Any]]:
        return [log for log in self._in_memory_logs if log.get("session_id") == session_id]


audit_logger = AuditLogger()
