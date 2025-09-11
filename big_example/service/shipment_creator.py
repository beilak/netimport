import datetime
import typing
import typing as tp

from big_example.domine.shipment import Shipment


class IShipmentRepository(tp.Protocol):
    def save(self, shipment: Shipment) -> None: ...


class ShipmentCreator:
    def __init__(self, shipment_repository: IShipmentRepository) -> None:
        self._shipment_repository = shipment_repository

    def new(self, order_id: int, shipment_date: datetime.date, carrier: str, tracking_number: str) -> Shipment:
        new_shipment: typing.Final = Shipment(
            id=0, order_id=order_id, shipment_date=shipment_date, carrier=carrier, tracking_number=tracking_number
        )
        self._shipment_repository.save(new_shipment)

        return new_shipment
