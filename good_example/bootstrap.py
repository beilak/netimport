from dataclasses import dataclass

from good_example.repo import AccountRepository, UserRepository
from good_example.service import AccountCreator, UserCreator


@dataclass(frozen=True, slots=True)
class DemoServices:
    account_creator: AccountCreator
    user_creator: UserCreator


def build_demo_services() -> DemoServices:
    return DemoServices(
        account_creator=AccountCreator(account_repository=AccountRepository()),
        user_creator=UserCreator(user_repository=UserRepository()),
    )


def run_demo() -> None:
    services = build_demo_services()
    services.account_creator.new("Primary account")
    services.user_creator.new("demo-user")
