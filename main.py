# main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.waiting_connections: List[WebSocket] = []
        self.active_pairs: Dict[WebSocket, WebSocket] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        await self.match(websocket)

    async def match(self, websocket: WebSocket):
        if self.waiting_connections:
            peer = self.waiting_connections.pop(0)
            self.active_pairs[websocket] = peer
            self.active_pairs[peer] = websocket
            await websocket.send_json({"type": "match_found"})
            await peer.send_json({"type": "match_found"})
        else:
            self.waiting_connections.append(websocket)
            await websocket.send_json({"type": "waiting"})

    def disconnect(self, websocket: WebSocket):
        if websocket in self.waiting_connections:
            self.waiting_connections.remove(websocket)
        if websocket in self.active_pairs:
            peer = self.active_pairs.pop(websocket)
            self.active_pairs.pop(peer, None)
            return peer
        return None

    async def send_message(self, message: dict, websocket: WebSocket):
        recipient = self.active_pairs.get(websocket)
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
                peer = manager.disconnect(websocket)
                if peer:
                    await peer.send_json({'type': 'peer_left'})
                await websocket.close()
                break
            elif data['type'] == 'ready':
                peer = manager.disconnect(websocket)
                if peer:
                    await peer.send_json({'type': 'peer_left'})
                await manager.match(websocket)
            else:
                await manager.send_message(data, websocket)
    except WebSocketDisconnect:
        peer = manager.disconnect(websocket)
        if peer:
            await peer.send_json({'type': 'peer_left'})
        await websocket.close()