from good_example.entities import Account


class AccountRepository:
    def __init__(self) -> None:
        self._saved_accounts: list[Account] = []

    def save(self, account: Account) -> None:
        self._saved_accounts.append(account)
