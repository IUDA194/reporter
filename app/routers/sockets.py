import uuid
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.database import redis
from app.auth import BOT_URL

router = APIRouter()

active_connections = {}

@router.get("/ws/login", include_in_schema=True, tags=["WebSocket"])
def websocket_info():
    """
    **WebSocket Endpoint**  
    Connect to `ws://<host>/ws/login` or `wss://<host>/ws/login` using WebSocket.  
    Optional query param: `referred_by` (string).  

    **Usage:**
    - On connect, receive `{ "uuid": "<uuid>", "bot_url": "<bot_link>" }`
    - Send JSON `{"jwt": "<your_token>"}` to save token in Redis.
    - On disconnect, session UUID is removed.

    ⚠ This is a placeholder to display WebSocket usage in docs.
    """
    return JSONResponse({
        "detail": "Use WebSocket at /ws/login — this is just a documentation helper."
    })

@router.websocket("/login")
@router.websocket("/login/")
async def websocket_endpoint(websocket: WebSocket, referred_by: str = Query(default=None)):
    await websocket.accept()
    session_uuid = str(uuid.uuid4())
    await redis.set(session_uuid, "connected", ex=600)

    bot_url = f"{BOT_URL}?start=uuid_{session_uuid}"
    if referred_by:
        bot_url += f"_ref_{referred_by}"

    await websocket.send_text(json.dumps({
        "uuid": session_uuid,
        "bot_url": bot_url
    }))

    active_connections[session_uuid] = websocket

    try:
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            jwt_payload = data.get("jwt")
            if jwt_payload:
                await redis.set(f"jwt:{session_uuid}", jwt_payload, ex=600)
                await websocket.send_text(json.dumps({"status": "jwt_saved"}))
            else:
                await websocket.send_text(json.dumps({"error": "JWT not found"}))
    except WebSocketDisconnect:
        await redis.delete(session_uuid)
        active_connections.pop(session_uuid, None)
