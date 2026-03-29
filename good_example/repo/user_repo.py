from good_example.entities import User


class UserRepository:
    def __init__(self) -> None:
        self._saved_users: list[User] = []

    def save(self, user: User) -> None:
        self._saved_users.append(user)
