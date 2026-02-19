from dataclasses import dataclass

import pytest

from app.shared_kernel.application.command import Command
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.application.mediator import Mediator
from app.shared_kernel.application.query import Query
from app.shared_kernel.application.query_handler import QueryHandler


@dataclass(frozen=True)
class AddNumbers(Command):
    a: int = 0
    b: int = 0


class AddNumbersHandler(CommandHandler[AddNumbers, int]):
    async def handle(self, command: AddNumbers) -> int:
        return command.a + command.b


@dataclass(frozen=True)
class GetGreeting(Query):
    name: str = ""


class GetGreetingHandler(QueryHandler[GetGreeting, str]):
    async def handle(self, query: GetGreeting) -> str:
        return f"Hello, {query.name}!"


class TestMediator:
    def _make_mediator(self) -> Mediator:
        mediator = Mediator()
        mediator.register_command_handler(AddNumbers, lambda: AddNumbersHandler())
        mediator.register_query_handler(GetGreeting, lambda: GetGreetingHandler())
        return mediator

    async def test_send_command(self) -> None:
        mediator = self._make_mediator()
        result = await mediator.send(AddNumbers(a=2, b=3))
        assert result == 5

    async def test_send_query(self) -> None:
        mediator = self._make_mediator()
        result = await mediator.query(GetGreeting(name="World"))
        assert result == "Hello, World!"

    async def test_unregistered_command_raises(self) -> None:
        mediator = Mediator()
        with pytest.raises(KeyError):
            await mediator.send(AddNumbers(a=1, b=2))

    async def test_unregistered_query_raises(self) -> None:
        mediator = Mediator()
        with pytest.raises(KeyError):
            await mediator.query(GetGreeting(name="Test"))
