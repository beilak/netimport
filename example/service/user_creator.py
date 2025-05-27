import typing
import typing as tp
from decimal import Decimal

from example.domine.user import User


class IUserRepository(tp.Protocol):
    def save(self, user: User) -> None: ...


class UserCreator:
    def __init__(self, user_repository: IUserRepository):
        self._user_repository = user_repository

    def new(self, name: str) -> User:
        new_user: typing.Final = User(name=name)
        self._user_repository.save(new_user)


        return new_user
