from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from auth.auth_security import decode_access_token
import redis.asyncio as aioredis


router = APIRouter()

@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    payload = decode_access_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return 
    
    user_id = payload['userId']

    await websocket.accept()
    print(f"User {user_id} ({payload['username']}) connected via WebSocket")

    redis_client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"user_notifications:{user_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        print(f"User {user_id} disconnected")
    finally:
        await pubsub.unsubscribe(f"user_notification:{user_id}")
        await redis_client.close()