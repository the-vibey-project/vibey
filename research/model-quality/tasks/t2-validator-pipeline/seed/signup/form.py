from dataclasses import dataclass


@dataclass(frozen=True)
class SignupForm:
    username: str
    email: str
    age: int


@dataclass(frozen=True)
class User:
    username: str
    email: str
    age: int
