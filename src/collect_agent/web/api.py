"""FastAPI routes for the web simulation dashboard."""

from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserProfile, UserState
from collect_agent.main import CollectAgentSystem
from collect_agent.web.ws import ConnectionManager

app = FastAPI(title="Collect Agent Simulator")
system = CollectAgentSystem.from_config()
manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def index():
    from pathlib import Path

    html_path = Path(__file__).parents[3] / "web" / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>Collect Agent Simulator</h1><p>index.html not found</p>"


@app.post("/api/users")
async def create_user(data: dict):
    user_id = data.get("user_id", "test_001")
    state = UserState(
        user_id=user_id,
        profile=UserProfile(
            user_id=user_id,
            name=data.get("name", "张三"),
            overdue_days=data.get("overdue_days", 5),
            amount_due=data.get("amount_due", 1000.0),
            occupation=data.get("occupation"),
        ),
    )
    system.store.save(state)
    return {"user_id": user_id, "status": "created"}


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    session = system.session_manager.get_or_create(user_id)
    return {
        "user_id": user_id,
        "session_state": session.user_state.session_state,
        "current_intent": session.user_state.conversation.current_intent,
        "negotiation_round": session.user_state.conversation.negotiation_round,
        "messages": [
            {
                "direction": m.direction,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in session.user_state.conversation.messages
        ],
    }


@app.post("/api/events")
async def send_event(data: dict):
    user_id = data["user_id"]
    event_type = EventType(data["event_type"].lower())
    payload = data.get("payload", {})

    event = Event(user_id=user_id, type=event_type, payload=payload)
    session = system.session_manager.get_or_create(user_id)
    result = await session.handle_event(event)

    return {
        "status": result.status if result else "none",
        "response_text": result.response_text if result else None,
        "thinking": result.thinking[:500] if result and result.thinking else None,
        "new_session_state": result.new_session_state if result else None,
        "intent": session.user_state.conversation.current_intent,
    }


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            event_type = EventType(data["event_type"].lower())
            payload = data.get("payload", {})

            event = Event(user_id=user_id, type=event_type, payload=payload)
            session = system.session_manager.get_or_create(user_id)
            result = await session.handle_event(event)

            await manager.broadcast(
                {
                    "type": "agent_response",
                    "user_id": user_id,
                    "status": result.status if result else "none",
                    "response_text": result.response_text if result else None,
                    "thinking": result.thinking[:500] if result and result.thinking else None,
                    "new_session_state": result.new_session_state if result else None,
                    "intent": session.user_state.conversation.current_intent,
                    "session_state": session.user_state.session_state,
                    "negotiation_round": session.user_state.conversation.negotiation_round,
                },
                user_id,
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
