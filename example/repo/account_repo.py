from example.domine.account import Account


class AccountRepository:
    def __init__(self) -> None:
        self._some_obj = None

    def save(self, account: Account) -> None:
        print(self._some_obj)
        print(account)
