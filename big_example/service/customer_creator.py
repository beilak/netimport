import typing
import typing as tp

from big_example.domine.customer import Customer


class ICustomerRepository(tp.Protocol):
    def save(self, customer: Customer) -> None: ...


class CustomerCreator:
    def __init__(self, customer_repository: ICustomerRepository) -> None:
        self._customer_repository = customer_repository

    def new(self, first_name: str, last_name: str, email: str, phone: str, address_id: int) -> Customer:
        new_customer: typing.Final = Customer(
            id=0, first_name=first_name, last_name=last_name, email=email, phone=phone, address_id=address_id
        )
        self._customer_repository.save(new_customer)

        return new_customer
