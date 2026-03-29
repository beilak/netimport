"""Repository ports used by the low-coupling example."""

from typing import Protocol

from good_example.entities import Account, User


class AccountWriter(Protocol):
    def save(self, account: Account) -> None: ...


class UserWriter(Protocol):
    def save(self, user: User) -> None: ...
