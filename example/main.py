import typing

from example.repo.account_repo import AccountRepository
from repo.account_repo import AccountRepository as RepoTest
from example.service.account_creator import AccountCreator
from service.account_creator import AccountCreator as AccountCreatorForTest


AnyStr = typing.TypeVar("AnyStr", str, bytes)


def main(welcome_text: AnyStr) -> None:
    print(welcome_text)
    creator = AccountCreator(account_repository=AccountRepository())
    print(creator)
    print(AccountCreatorForTest)
    print(RepoTest)
    creator.new("Test")


if __name__ == "__main__":
    main("Hello World!")
