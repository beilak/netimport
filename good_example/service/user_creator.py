from good_example.entities import User
from good_example.ports import UserWriter


class UserCreator:
    def __init__(self, user_repository: UserWriter) -> None:
        self._user_repository = user_repository

    def new(self, name: str) -> User:
        new_user = User(name=name)
        self._user_repository.save(new_user)

        return new_user
