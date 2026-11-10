from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
