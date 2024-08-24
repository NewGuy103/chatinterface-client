import asyncio
import uuid

import websockets
import msgpack

from typing import Callable, Any
from ..config import simple_log_setup


logger = simple_log_setup()


class WSClient:
    def __init__(self, ws_host: str) -> None:
        self.__token: str = ''
        self.ws_uri: str = ws_host

        self._handlers: dict[str, Callable[[dict], Any]] = {}

    async def _init_ws(self, session_token: str) -> tuple[str | int, Exception | None]:
        try:
            self.ws: websockets.WebSocketClientProtocol = await websockets.connect(self.ws_uri)
        except websockets.exceptions.InvalidURI:
            return ("INVALID_URI", None)
        except OSError as e:
            logger.exception("OSError while attempting to open new WebSocket connection:")
            return ("OS_ERROR", e)

        auth_info: dict[str, str] = {'session_token': session_token}
        try:
            await self.ws.send(msgpack.packb(auth_info))
            await asyncio.wait_for(self.ws.recv(), timeout=20)
        except websockets.ConnectionClosed as e:
            logger.exception("Connection closed during authentication:")
            return ("CONNECTION_CLOSED", e)
        except asyncio.TimeoutError as e:
            logger.error("Waited for server to respond after authentication, no response!")
            return ("WAIT_TIMEOUT", e)
        
        logger.debug("Connected to WebSocket server '%s'", self.ws_uri)
        return (0, None)

    async def setup(self, session_token: str) -> tuple[str | int, Exception | None]:
        if not session_token:
            raise ValueError("session token required to authenticate")

        init_ws_result: tuple[str | int, Exception | None] = await self._init_ws(session_token)
        if init_ws_result[0] != 0:
            return init_ws_result

        self._connected: bool = True
        self.handler_task: asyncio.Task = asyncio.create_task(self.message_handler())

        self.__token: str = session_token
        return (0, None)

    async def reconnect(self) -> tuple[str | int, Exception | None]:
        await self.close()  # when closing existing socket: might call error.closed if not already closed
        init_ws_result: tuple[str | int, Exception | None] = await self._init_ws(self.__token)
        if init_ws_result[0] != 0:
            return init_ws_result

        self._connected: bool = True
        self.handler_task: asyncio.Task = asyncio.create_task(self.message_handler())

        return (0, None)

    async def close(self):
        await self.ws.close(code=1000)
        self._connected: bool = False

    async def send_message(self, message_type: str, message_data: dict):
        if not self._connected:
            raise RuntimeError("websocket is not yet connected")

        if not isinstance(message_type, str):
            raise TypeError("message type is not a string!")
        
        if not isinstance(message_data, dict):
            raise TypeError("message data must be a dictionary!")
        
        msg_dict: dict = {
            'message': message_type,
            'data': message_data
        }
        await self.ws.send(msgpack.packb(msg_dict))

    def add_handler(self, message_type: str, handler: Callable[[dict], Any]) -> str:
        if not isinstance(message_type, str):
            raise TypeError("message type is not a string")

        if not callable(handler):
            raise ValueError("handler object is not callable")

        handler_id: str = str(uuid.uuid4())
        if message_type not in self._handlers:
            self._handlers[message_type] = {}
        
        self._handlers[message_type][handler_id] = handler
        return handler_id

    def remove_handler(self, handler_id: str) -> int:
        if not isinstance(handler_id, str):
            raise TypeError("message type is not a string")

        for handler_dict in self._handlers.values():
            if not handler_dict.get(handler_id):
                continue

            del handler_dict[handler_id]
            return 0

        return 1

    def _call_handlers(self, message_type: str, data: dict):
        handlers: dict = {}
        for handler_type, handler_dict in self._handlers.items():
            if handler_type != message_type:
                continue

            handlers: dict = handler_dict
            break

        if not handlers:
            logger.warning("No handlers registered for message type '%s'", message_type)
            return

        for handler_id, handler in handlers.items():
            loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
            try:
                if asyncio.iscoroutinefunction(handler):
                    loop.create_task(handler(data))
                else:
                    asyncio.to_thread(handler, data)
            except Exception:
                logger.exception(
                    "Handler ID '%s' for message '%s' threw an error:", 
                    handler_id, message_type
                )

        return

    async def message_handler(self):
        while self._connected:
            try:
                message: bytes = await self.ws.recv()
            except websockets.ConnectionClosed as e:
                logger.warning("WebSocket Connection closed:", exc_info=e)
                self._call_handlers("error.closed", {
                    'code': e.code,
                    'reason': e.reason,
                    'exc': e
                })
                break

            try:
                data: bytes = msgpack.unpackb(message)
                if not isinstance(data, dict):
                    raise ValueError("did not get a dictionary as the unpacked message")
            except Exception as e:
                logger.exception("Server MessagePack data is not valid!")
                self._call_handlers("error.data_invalid", {'exc': e})
                break

            msg_type: str = data.get('message')
            msg_data: dict = data.get('data')

            self._call_handlers(msg_type, msg_data)
        await self.close()
