# backend/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import uuid

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.waiting_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        if self.waiting_connections:
            peer = self.waiting_connections.pop(0)
            await websocket.send_json({"type": "match_found"})
            await peer.send_json({"type": "match_found"})
            self.active_connections.extend([websocket, peer])
        else:
            self.waiting_connections.append(websocket)
            await websocket.send_json({"type": "waiting"})

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        elif websocket in self.waiting_connections:
            self.waiting_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        recipient = None
        for conn in self.active_connections:
            if conn != websocket:
                recipient = conn
                break
        if recipient:
            await recipient.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'leave':
                manager.disconnect(websocket)
                await websocket.close()
                break
            else:
                await manager.send_message(data, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await websocket.close()
