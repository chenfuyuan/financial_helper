from collections.abc import Callable
from typing import Any

from .command import Command
from .command_handler import CommandHandler
from .query import Query
from .query_handler import QueryHandler


class Mediator:
    def __init__(self) -> None:
        self._command_handlers: dict[type[Command], Callable[[], CommandHandler[Any, Any]]] = {}
        self._query_handlers: dict[type[Query], Callable[[], QueryHandler[Any, Any]]] = {}

    def register_command_handler(
        self,
        command_type: type[Command],
        factory: Callable[[], CommandHandler[Any, Any]],
    ) -> None:
        self._command_handlers[command_type] = factory

    def register_query_handler(
        self,
        query_type: type[Query],
        factory: Callable[[], QueryHandler[Any, Any]],
    ) -> None:
        self._query_handlers[query_type] = factory

    async def send(self, command: Command) -> Any:
        handler_factory = self._command_handlers[type(command)]
        handler = handler_factory()
        return await handler.handle(command)

    async def query(self, query: Query) -> Any:
        handler_factory = self._query_handlers[type(query)]
        handler = handler_factory()
        return await handler.handle(query)
