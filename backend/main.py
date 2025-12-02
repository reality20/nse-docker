import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from nse_client import NSEClient
import json
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nse_client = NSEClient()
# Initialize cookies on startup
nse_client.refresh_cookies()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                # We might want to disconnect here, but for now let's just log

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background task to poll NSE and broadcast updates
async def broadcast_market_data():
    while True:
        try:
            data = nse_client.get_nifty_price()
            if data:
                # Add current server time for latency check if needed
                data['server_time'] = time.time()
                message = json.dumps(data)
                await manager.broadcast(message)
            else:
                logger.warning("No data received from NSE client")
        except Exception as e:
            logger.error(f"Error in broadcast loop: {e}")

        # Poll every 2 seconds. NSE updates aren't super fast, but 2s is decent for 'tick' feel
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_market_data())

@app.get("/")
def read_root():
    return {"status": "ok", "message": "NSE Trading Backend is running"}
