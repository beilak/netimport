import datetime
import typing
import typing as tp

from big_example.domine.promotion import Promotion


class IPromotionRepository(tp.Protocol):
    def save(self, promotion: Promotion) -> None: ...


class PromotionCreator:
    def __init__(self, promotion_repository: IPromotionRepository) -> None:
        self._promotion_repository = promotion_repository

    def new(self, code: str, description: str, discount_percentage: float, start_date: datetime.date, end_date: datetime.date) -> Promotion:
        new_promotion: typing.Final = Promotion(id=0, code=code, description=description, discount_percentage=discount_percentage, start_date=start_date, end_date=end_date)
        self._promotion_repository.save(new_promotion)

        return new_promotion
