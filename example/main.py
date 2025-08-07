import typing

from example.repo.account_repo import AccountRepository
from example.repo.user_repo import UserRepository
from example.service.account_creator import AccountCreator
from example.service.user_creator import UserCreator


AnyStr = typing.TypeVar("AnyStr", str, bytes)


def main(welcome_text: AnyStr) -> None:
    creator = AccountCreator(account_repository=AccountRepository())
    creator.new("Test")

    user_creator = UserCreator(user_repository=UserRepository())
    user_creator.new("test")



if __name__ == "__main__":
    main("Hello World!")
