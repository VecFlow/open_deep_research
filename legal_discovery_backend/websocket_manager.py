"""
WebSocket Manager for Legal Discovery Backend.
Handles real-time communication with frontend clients.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""
    client_id: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    case_ids: Set[str] = field(default_factory=set)
    last_ping: datetime = field(default_factory=datetime.utcnow)

class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.case_subscriptions: Dict[str, Set[str]] = {}  # case_id -> set of client_ids
        self._ping_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        try:
            await websocket.accept()
            
            connection = WebSocketConnection(
                client_id=client_id,
                websocket=websocket,
                connected_at=datetime.utcnow()
            )
            
            self.connections[client_id] = connection
            
            # Start background tasks if not already running
            if not self._ping_task:
                self._ping_task = asyncio.create_task(self._ping_clients())
            
            if not self._cleanup_task:
                self._cleanup_task = asyncio.create_task(self._cleanup_connections())
            
            # Send welcome message
            await self._send_to_client(client_id, {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to Legal Discovery Backend"
            })
            
            logger.info(f"WebSocket client {client_id} connected")
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket client {client_id}: {e}")
            raise
    
    async def disconnect(self, client_id: str) -> None:
        """Disconnect a WebSocket client and cleanup."""
        try:
            connection = self.connections.get(client_id)
            if not connection:
                return
            
            # Remove from case subscriptions
            for case_id in connection.case_ids:
                if case_id in self.case_subscriptions:
                    self.case_subscriptions[case_id].discard(client_id)
                    if not self.case_subscriptions[case_id]:
                        del self.case_subscriptions[case_id]
            
            # Remove connection
            del self.connections[client_id]
            
            logger.info(f"WebSocket client {client_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket client {client_id}: {e}")
    
    async def handle_message(self, client_id: str, message: Dict[str, Any]) -> None:
        """Handle incoming message from WebSocket client."""
        try:
            message_type = message.get("type")
            
            if message_type == "subscribe_case":
                case_id = message.get("case_id")
                if case_id:
                    await self._subscribe_to_case(client_id, case_id)
            
            elif message_type == "unsubscribe_case":
                case_id = message.get("case_id")
                if case_id:
                    await self._unsubscribe_from_case(client_id, case_id)
            
            elif message_type == "ping":
                await self._handle_ping(client_id)
            
            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
    
    async def _subscribe_to_case(self, client_id: str, case_id: str) -> None:
        """Subscribe a client to updates for a specific case."""
        try:
            connection = self.connections.get(client_id)
            if not connection:
                return
            
            # Add to case subscriptions
            if case_id not in self.case_subscriptions:
                self.case_subscriptions[case_id] = set()
            
            self.case_subscriptions[case_id].add(client_id)
            connection.case_ids.add(case_id)
            
            # Send confirmation
            await self._send_to_client(client_id, {
                "type": "subscribed_to_case",
                "case_id": case_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.debug(f"Client {client_id} subscribed to case {case_id}")
            
        except Exception as e:
            logger.error(f"Error subscribing client {client_id} to case {case_id}: {e}")
    
    async def _unsubscribe_from_case(self, client_id: str, case_id: str) -> None:
        """Unsubscribe a client from updates for a specific case."""
        try:
            connection = self.connections.get(client_id)
            if not connection:
                return
            
            # Remove from case subscriptions
            if case_id in self.case_subscriptions:
                self.case_subscriptions[case_id].discard(client_id)
                if not self.case_subscriptions[case_id]:
                    del self.case_subscriptions[case_id]
            
            connection.case_ids.discard(case_id)
            
            # Send confirmation
            await self._send_to_client(client_id, {
                "type": "unsubscribed_from_case",
                "case_id": case_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.debug(f"Client {client_id} unsubscribed from case {case_id}")
            
        except Exception as e:
            logger.error(f"Error unsubscribing client {client_id} from case {case_id}: {e}")
    
    async def _handle_ping(self, client_id: str) -> None:
        """Handle ping message from client."""
        try:
            connection = self.connections.get(client_id)
            if connection:
                connection.last_ping = datetime.utcnow()
                
                await self._send_to_client(client_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error handling ping from client {client_id}: {e}")
    
    async def _send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific client."""
        try:
            connection = self.connections.get(client_id)
            if not connection:
                return False
            
            await connection.websocket.send_text(json.dumps(message))
            return True
            
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected during message send")
            await self.disconnect(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            await self.disconnect(client_id)
            return False
    
    async def broadcast_to_case(self, case_id: str, message: Dict[str, Any]) -> int:
        """Broadcast message to all clients subscribed to a case."""
        try:
            subscribers = self.case_subscriptions.get(case_id, set())
            if not subscribers:
                return 0
            
            # Add case_id to message
            message["case_id"] = case_id
            
            # Send to all subscribers
            successful_sends = 0
            failed_clients = []
            
            for client_id in subscribers:
                success = await self._send_to_client(client_id, message)
                if success:
                    successful_sends += 1
                else:
                    failed_clients.append(client_id)
            
            # Clean up failed connections
            for client_id in failed_clients:
                await self.disconnect(client_id)
            
            if successful_sends > 0:
                logger.debug(f"Broadcast message to {successful_sends} clients for case {case_id}")
            
            return successful_sends
            
        except Exception as e:
            logger.error(f"Error broadcasting to case {case_id}: {e}")
            return 0
    
    async def broadcast_to_all(self, message: Dict[str, Any]) -> int:
        """Broadcast message to all connected clients."""
        try:
            if not self.connections:
                return 0
            
            successful_sends = 0
            failed_clients = []
            
            for client_id in list(self.connections.keys()):
                success = await self._send_to_client(client_id, message)
                if success:
                    successful_sends += 1
                else:
                    failed_clients.append(client_id)
            
            # Clean up failed connections
            for client_id in failed_clients:
                await self.disconnect(client_id)
            
            if successful_sends > 0:
                logger.debug(f"Broadcast message to {successful_sends} clients")
            
            return successful_sends
            
        except Exception as e:
            logger.error(f"Error broadcasting to all clients: {e}")
            return 0
    
    async def _ping_clients(self) -> None:
        """Periodically ping clients to keep connections alive."""
        while True:
            try:
                await asyncio.sleep(30)  # Ping every 30 seconds
                
                if not self.connections:
                    continue
                
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                failed_clients = []
                for client_id in list(self.connections.keys()):
                    success = await self._send_to_client(client_id, ping_message)
                    if not success:
                        failed_clients.append(client_id)
                
                # Clean up failed connections
                for client_id in failed_clients:
                    await self.disconnect(client_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ping task: {e}")
    
    async def _cleanup_connections(self) -> None:
        """Periodically clean up stale connections."""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
                now = datetime.utcnow()
                stale_clients = []
                
                for client_id, connection in self.connections.items():
                    # Remove connections that haven't pinged in 10 minutes
                    if (now - connection.last_ping).total_seconds() > 600:
                        stale_clients.append(client_id)
                
                for client_id in stale_clients:
                    logger.info(f"Cleaning up stale connection: {client_id}")
                    await self.disconnect(client_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup all connections and background tasks."""
        try:
            # Cancel background tasks
            if self._ping_task:
                self._ping_task.cancel()
                try:
                    await self._ping_task
                except asyncio.CancelledError:
                    pass
            
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Close all connections
            for client_id in list(self.connections.keys()):
                await self.disconnect(client_id)
            
            logger.info("WebSocket manager cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during WebSocket manager cleanup: {e}")
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)
    
    def get_case_subscriber_count(self, case_id: str) -> int:
        """Get the number of subscribers for a specific case."""
        return len(self.case_subscriptions.get(case_id, set()))
    
    def get_active_cases(self) -> List[str]:
        """Get list of cases with active subscribers."""
        return list(self.case_subscriptions.keys())

# Global instance
websocket_manager = WebSocketManager()