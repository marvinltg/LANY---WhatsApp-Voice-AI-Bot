import time
import uuid
import logging
from enum import Enum

logger = logging.getLogger("LANY.SessionManager")

class CallState(Enum):
    IDLE = "IDLE"
    INCOMING = "INCOMING"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"

class SessionManager:
    def __init__(self):
        self.current_session = None

    def start_session(self, caller_info: str = "Unknown Caller") -> dict:
        session_id = str(uuid.uuid4())[:8]
        self.current_session = {
            "call_id": session_id,
            "caller": caller_info,
            "started_at": time.time(),
            "last_activity": time.time(),
            "history": [],
            "state": CallState.CONNECTING.value
        }
        logger.info(f"[SESSION START] Started new call session {session_id} for caller: {caller_info}")
        return self.current_session

    def update_state(self, new_state: CallState):
        if self.current_session:
            self.current_session["state"] = new_state.value
            self.current_session["last_activity"] = time.time()
            logger.info(f"[SESSION STATE] State changed to: {new_state.value}")

    def add_history(self, role: str, text: str):
        if self.current_session and text:
            self.current_session["history"].append({
                "role": role,
                "text": text,
                "timestamp": time.time()
            })
            logger.debug(f"[SESSION HISTORY] Added {role}: {text}")

    def get_history(self) -> list:
        if self.current_session:
            return self.current_session.get("history", [])
        return []

    def end_session(self):
        if self.current_session:
            session_id = self.current_session.get("call_id")
            logger.info(f"[SESSION END] Cleaned up call session {session_id}")
            self.current_session = None

    def get_state(self) -> str:
        if self.current_session:
            return self.current_session.get("state", CallState.IDLE.value)
        return CallState.IDLE.value
