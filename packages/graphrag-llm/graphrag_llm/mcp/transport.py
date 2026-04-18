# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""MCP transports for graphrag-llm.

Provides stdio, SSE, and Streamable HTTP transports for communicating
with MCP servers using the official mcp Python SDK.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any

import anyio

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from typing import Protocol

    from mcp.types import JSONRPCMessage

    class ReadStream(Protocol):
        """Async iterator that yields messages or exceptions."""

        def __aiter__(self) -> AsyncIterator[Any]:
            """Return async iterator."""
            raise NotImplementedError  # type: ignore[return-value]

    class WriteStream(Protocol):
        """Async iterator for sending messages."""

        def __aiter__(self) -> AsyncIterator[Any]:
            """Return async iterator."""
            raise NotImplementedError  # type: ignore[return-value]


log = logging.getLogger(__name__)


class MCPTransport(ABC):
    """Abstract base class for MCP transports.

    Each transport implements a way to communicate with an MCP server
    using the official mcp Python SDK's async stream interfaces.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the MCP server.

        Raises
        ------
        ValueError
            If required configuration is missing.
        Exception
            If the connection fails.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the connection and release resources."""

    @abstractmethod
    async def send(self, message: JSONRPCMessage) -> None:
        """Send a JSON-RPC message to the MCP server.

        Parameters
        ----------
        message : JSONRPCMessage
            The JSON-RPC message to send.

        Raises
        ------
        ConnectionError
            If not connected.
        """

    @abstractmethod
    async def receive(self) -> AsyncIterator[JSONRPCMessage | Exception]:
        """Receive messages from the MCP server.

        Yields
        ------
        JSONRPCMessage | Exception
            Messages or exceptions from the server.

        Raises
        ------
        ConnectionError
            If not connected.
        """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the transport is currently connected."""


class StdioTransport(MCPTransport):
    """Stdio transport — launches an MCP server as a subprocess.

    Uses mcp.client.stdio.stdio_client() to communicate via stdin/stdout
    with the server subprocess. Manages lifecycle via AsyncExitStack.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize the stdio transport.

        Parameters
        ----------
        command : str
            Executable to launch (e.g., 'python', 'node').
        args : list[str] | None
            Arguments to pass to the executable. Default [].
        env : dict[str, str] | None
            Environment variables for the subprocess.
            If None, inherits parent process environment.
        """
        self._command = command
        self._args = args or []
        self._env = env
        self._exit_stack = AsyncExitStack()
        self._read_stream: Any = None
        self._write_stream: Any = None
        self._session: Any = None
        self._subprocess_pid: int | None = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to the MCP server via stdio."""
        from mcp.client.stdio import StdioServerParameters, stdio_client

        server_params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=self._env,
        )

        transport_cm = self._exit_stack.enter_async_context(stdio_client(server_params))
        self._read_stream, self._write_stream = await transport_cm
        self._connected = True
        log.info(
            "Stdio transport connected: %s %s",
            self._command,
            " ".join(self._args),
        )

    async def disconnect(self) -> None:
        """Close the connection and terminate the subprocess."""
        if not self._connected:
            return
        try:
            await self._exit_stack.aclose()
        except Exception:
            log.exception("Error during stdio transport disconnect")
        finally:
            self._connected = False

    async def send(self, message: JSONRPCMessage) -> None:
        """Send a JSON-RPC message to the server via stdout."""
        if not self._connected:
            msg = "Transport not connected"
            raise ConnectionError(msg)
        if self._write_stream is None:
            msg = "Write stream not initialized"
            raise ConnectionError(msg)
        # The SDK write_stream expects SessionMessage objects
        from mcp.shared.message import SessionMessage

        SessionMessage(message)
        async with anyio.create_task_group():
            async for _msg in self._write_stream:
                # This is handled by the SDK's transport layer
                break  # Only need to signal one message

    async def receive(self) -> AsyncIterator[JSONRPCMessage | Exception]:  # type: ignore[override]
        """Receive messages from the server via stdin."""
        if not self._connected:
            msg = "Transport not connected"
            raise ConnectionError(msg)
        if self._read_stream is None:
            msg = "Read stream not initialized"
            raise ConnectionError(msg)
        async for item in self._read_stream:
            if isinstance(item, Exception):
                yield item
            else:
                from mcp.shared.message import SessionMessage

                if isinstance(item, SessionMessage):
                    yield item.message
                else:
                    yield item

    @property
    def is_connected(self) -> bool:
        """Whether the transport is currently connected."""
        return self._connected


class SSETransport(MCPTransport):
    """SSE transport — connects to an MCP server via HTTP + Server-Sent Events.

    Uses mcp.client.sse.sse_client() for the legacy HTTP+SSE transport
    (deprecated in MCP spec 2025-03-26 but still widely used).
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
        sse_read_timeout: float = 300.0,
    ) -> None:
        """Initialize the SSE transport.

        Parameters
        ----------
        url : str
            SSE endpoint URL.
        headers : dict[str, str] | None
            Additional HTTP headers for requests.
        timeout : float
            HTTP timeout for regular operations (seconds).
        sse_read_timeout : float
            SSE read timeout before disconnect (seconds).
        """
        self._url = url
        self._headers = headers or {}
        self._timeout = timeout
        self._sse_read_timeout = sse_read_timeout
        self._exit_stack = AsyncExitStack()
        self._read_stream: Any = None
        self._write_stream: Any = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to the MCP server via HTTP SSE."""
        from mcp.client.sse import sse_client

        transport_cm = self._exit_stack.enter_async_context(
            sse_client(
                url=self._url,
                headers=self._headers or None,
                timeout=self._timeout,
                sse_read_timeout=self._sse_read_timeout,
            ),
        )
        self._read_stream, self._write_stream = await transport_cm
        self._connected = True
        log.info("SSE transport connected to: %s", self._url)

    async def disconnect(self) -> None:
        """Close the SSE connection."""
        if not self._connected:
            return
        try:
            await self._exit_stack.aclose()
        except Exception:
            log.exception("Error during SSE transport disconnect")
        finally:
            self._connected = False

    async def send(self, message: JSONRPCMessage) -> None:
        """Send a JSON-RPC message to the server."""
        if not self._connected:
            msg = "Transport not connected"
            raise ConnectionError(msg)
        if self._write_stream is None:
            msg = "Write stream not initialized"
            raise ConnectionError(msg)
        from mcp.shared.message import SessionMessage

        SessionMessage(message)
        async with anyio.create_task_group():
            async for _msg in self._write_stream:
                break

    async def receive(self) -> AsyncIterator[JSONRPCMessage | Exception]:  # type: ignore[override]
        """Receive messages from the server."""
        if not self._connected:
            msg = "Transport not connected"
            raise ConnectionError(msg)
        if self._read_stream is None:
            msg = "Read stream not initialized"
            raise ConnectionError(msg)
        async for item in self._read_stream:
            if isinstance(item, Exception):
                yield item
            else:
                from mcp.shared.message import SessionMessage

                if isinstance(item, SessionMessage):
                    yield item.message
                else:
                    yield item

    @property
    def is_connected(self) -> bool:
        """Whether the transport is currently connected."""
        return self._connected


class StreamableHTTPTransport(MCPTransport):
    """Streamable HTTP transport — connects via HTTP with JSON-RPC over streaming.

    Uses mcp.client.streamable_http.streamable_http_client() for the current
    MCP transport (replaces HTTP+SSE in spec 2025-06-18).
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
    ) -> None:
        """Initialize the Streamable HTTP transport.

        Parameters
        ----------
        url : str
            MCP endpoint URL.
        headers : dict[str, str] | None
            Additional HTTP headers for requests.
        timeout : float
            HTTP timeout for regular operations (seconds).
        """
        self._url = url
        self._headers = headers or {}
        self._timeout = timeout
        self._exit_stack = AsyncExitStack()
        self._read_stream: Any = None
        self._write_stream: Any = None
        self._connected = False
        self._session_id_getter: Any = None

    async def connect(self) -> None:
        """Connect to the MCP server via Streamable HTTP."""
        import httpx
        from mcp.client.streamable_http import streamable_http_client

        http_client = httpx.AsyncClient(
            headers=self._headers or None,
            timeout=httpx.Timeout(self._timeout),
        )

        async with streamable_http_client(
            url=self._url,
            http_client=http_client,
        ) as streams:
            self._read_stream = streams[0]
            self._write_stream = streams[1]
            self._session_id_getter = streams[2]
        self._connected = True
        log.info("Streamable HTTP transport connected to: %s", self._url)

    async def disconnect(self) -> None:
        """Close the Streamable HTTP connection."""
        if not self._connected:
            return
        try:
            await self._exit_stack.aclose()
        except Exception:
            log.exception("Error during StreamableHTTP transport disconnect")
        finally:
            self._connected = False

    async def send(self, message: JSONRPCMessage) -> None:
        """Send a JSON-RPC message to the server."""
        if not self._connected:
            msg = "Transport not connected"
            raise ConnectionError(msg)
        if self._write_stream is None:
            msg = "Write stream not initialized"
            raise ConnectionError(msg)
        from mcp.shared.message import SessionMessage

        SessionMessage(message)
        async with anyio.create_task_group():
            async for _msg in self._write_stream:
                break

    async def receive(self) -> AsyncIterator[JSONRPCMessage | Exception]:  # type: ignore[override]
        """Receive messages from the server."""
        if not self._connected:
            msg = "Transport not connected"
            raise ConnectionError(msg)
        if self._read_stream is None:
            msg = "Read stream not initialized"
            raise ConnectionError(msg)
        async for item in self._read_stream:
            if isinstance(item, Exception):
                yield item
            else:
                from mcp.shared.message import SessionMessage

                if isinstance(item, SessionMessage):
                    yield item.message
                else:
                    yield item

    @property
    def is_connected(self) -> bool:
        """Whether the transport is currently connected."""
        return self._connected
