from good_big_example.entities import Invoice


class InvoiceRepository:
    def __init__(self) -> None:
        self._some_obj = None

    def save(self, invoice: Invoice) -> None:
        pass
