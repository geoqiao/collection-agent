"""Enhanced state machine with flowing states and one-way doors."""

from enum import Enum


class AgentSessionState(Enum):
    # Flowing states (can transition freely)
    NORMAL = "normal"
    PENDING_ESCALATE = "pending_escalate"

    # One-way doors (irreversible)
    ESCALATED = "escalated"
    STOPPED = "stopped"
    CRISIS = "crisis"
    DISPUTED = "disputed"

    # Terminal states
    RESOLVED = "resolved"
    PAUSED = "paused"


ONE_WAY_DOOR_STATES = {
    AgentSessionState.ESCALATED,
    AgentSessionState.STOPPED,
    AgentSessionState.CRISIS,
    AgentSessionState.DISPUTED,
}

FLOWING_STATES = {
    AgentSessionState.NORMAL,
    AgentSessionState.PENDING_ESCALATE,
}


class StateMachine:
    def __init__(self, initial: AgentSessionState = AgentSessionState.NORMAL):
        self._current = initial
        self._history: list[AgentSessionState] = [initial]

    @property
    def current(self) -> AgentSessionState:
        return self._current

    @property
    def is_locked(self) -> bool:
        """True if in a one-way door state."""
        return self._current in ONE_WAY_DOOR_STATES

    @property
    def is_flowing(self) -> bool:
        return self._current in FLOWING_STATES

    def can_transition(self, target: AgentSessionState) -> bool:
        """Check if transition is allowed."""
        current = self._current

        # One-way doors: only allow transition to RESOLVED or PAUSED
        if current in ONE_WAY_DOOR_STATES:
            return target in {AgentSessionState.RESOLVED, AgentSessionState.PAUSED}

        # Flowing states can transition to anything except direct exit from one-way doors
        if current in FLOWING_STATES:
            return True

        # Terminal states: no outgoing transitions
        if current in {AgentSessionState.RESOLVED, AgentSessionState.PAUSED}:
            return False

        return False

    def transition(self, target: AgentSessionState) -> bool:
        if not self.can_transition(target):
            return False
        self._current = target
        self._history.append(target)
        return True

    def force_transition(self, target: AgentSessionState) -> None:
        """Force transition (for crisis override)."""
        self._current = target
        self._history.append(target)

    def get_history(self) -> list[AgentSessionState]:
        return self._history.copy()
