from src.core.constants import SessionState


class SessionStateMachine:
    TRANSITIONS = {
        SessionState.IDLE: [SessionState.OUTREACH_START],
        SessionState.OUTREACH_START: [SessionState.INTENT_DETECTED, SessionState.IDLE],
        SessionState.INTENT_DETECTED: [SessionState.FOLLOW_UP, SessionState.RESOLVED, SessionState.IDLE],
        SessionState.FOLLOW_UP: [SessionState.FOLLOW_UP, SessionState.RESOLVED, SessionState.IDLE],
        SessionState.RESOLVED: [SessionState.IDLE],
    }

    def __init__(self):
        self._current = SessionState.IDLE

    @property
    def current(self) -> SessionState:
        return self._current

    def can_transition(self, target: SessionState) -> bool:
        return target in self.TRANSITIONS.get(self._current, [])

    def transition(self, target: SessionState) -> None:
        if not self.can_transition(target):
            raise ValueError(f"Cannot transition from {self._current.value} to {target.value}")
        self._current = target
