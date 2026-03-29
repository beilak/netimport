import typing
import typing as tp

from good_big_example.entities import Address


class IAddressRepository(tp.Protocol):
    def save(self, address: Address) -> None: ...


class AddressCreator:
    def __init__(self, address_repository: IAddressRepository) -> None:
        self._address_repository = address_repository

    def new(self, street: str, city: str, state: str, zip_code: str, country: str) -> Address:
        new_address: typing.Final = Address(
            id=0, street=street, city=city, state=state, zip_code=zip_code, country=country
        )
        self._address_repository.save(new_address)

        return new_address
