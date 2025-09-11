import datetime
import typing
import typing as tp

from big_example.domine.payment import Payment


class IPaymentRepository(tp.Protocol):
    def save(self, payment: Payment) -> None: ...


class PaymentCreator:
    def __init__(self, payment_repository: IPaymentRepository) -> None:
        self._payment_repository = payment_repository

    def new(self, order_id: int, payment_date: datetime.date, amount: float, payment_method: str) -> Payment:
        new_payment: typing.Final = Payment(id=0, order_id=order_id, payment_date=payment_date, amount=amount, payment_method=payment_method)
        self._payment_repository.save(new_payment)

        return new_payment
