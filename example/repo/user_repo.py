import os
from example.domine.user import User


class UserRepository:
    def __init__(self) -> None:
        self._some_obj = None
        print(os.name)


    def save(self, user: User) -> None:
        print(self._some_obj)
        print(user)
