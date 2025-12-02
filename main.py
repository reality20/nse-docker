import asyncio
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
try:
    nse_client.refresh_cookies()
except Exception as e:
    logger.error(f"Failed to refresh cookies on startup: {e}")

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
        # iterate over a copy of the list to allow modification during iteration if needed
        # though remove() happens in disconnect, synchronous iteration is safer
        for connection in self.active_connections[:]:
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

# Serve Static Files
# We expect the frontend build to be in 'dist' directory
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    # For Vite, usually assets are in dist/assets.
    # But we also have favicon, index.html in root of dist.

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve index.html for any path not found (SPA routing)
        # But we must be careful not to hide API routes if we had HTTP API routes.
        # Currently we only have WebSocket at /ws.

        # Check if file exists in dist
        file_path = os.path.join("dist", full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # Default to index.html
        return FileResponse("dist/index.html")

else:
    logger.warning("'dist' directory not found. Frontend will not be served.")
