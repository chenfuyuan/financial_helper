from dataclasses import dataclass

from app.shared_kernel.application.command import Command


@dataclass(frozen=True)
class CreateNoteCommand(Command):
    title: str = ""
    content: str = ""
