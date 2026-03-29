import datetime
import typing
import typing as tp

from good_big_example.entities import Invoice


class IInvoiceRepository(tp.Protocol):
    def save(self, invoice: Invoice) -> None: ...


class InvoiceCreator:
    def __init__(self, invoice_repository: IInvoiceRepository) -> None:
        self._invoice_repository = invoice_repository

    def new(self, order_id: int, invoice_date: datetime.date, due_date: datetime.date, total_amount: float) -> Invoice:
        new_invoice: typing.Final = Invoice(
            id=0, order_id=order_id, invoice_date=invoice_date, due_date=due_date, total_amount=total_amount
        )
        self._invoice_repository.save(new_invoice)

        return new_invoice
