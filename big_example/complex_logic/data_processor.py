from big_example.domine.product import Product
from big_example.domine.order import Order
from big_example.domine.customer import Customer
from big_example.domine.address import Address
from big_example.domine.payment import Payment
from big_example.repo.product_repo import ProductRepository
from big_example.repo.order_repo import OrderRepository
from big_example.repo.customer_repo import CustomerRepository
from big_example.repo.address_repo import AddressRepository
from big_example.repo.payment_repo import PaymentRepository
from big_example.service.product_creator import ProductCreator
from big_example.service.order_creator import OrderCreator
from big_example.service.customer_creator import CustomerCreator
from big_example.service.address_creator import AddressCreator
from big_example.service.payment_creator import PaymentCreator
from big_example.utils import get_current_timestamp


class DataProcessor:
    def __init__(
        self,
        product_creator: ProductCreator,
        customer_creator: CustomerCreator,
        order_creator: OrderCreator,
    ) -> None:
        self.product_creator = product_creator
        self.customer_creator = customer_creator
        self.order_creator = order_creator

    def process_raw_data(self, raw_data: dict) -> None:
        print(f"Processing data at {get_current_timestamp()}")
        # In a real app, this would process raw data and create
        # new domain objects using the creators.
        if "customer" in raw_data:
            customer_data = raw_data["customer"]
            # self.customer_creator.new(...)
            print(f"Processing customer data: {customer_data}")
        if "product" in raw_data:
            product_data = raw_data["product"]
            # self.product_creator.new(...)
            print(f"Processing product data: {product_data}")
        print("Data processing complete.")


def main() -> None:
    product_repo = ProductRepository()
    customer_repo = CustomerRepository()
    order_repo = OrderRepository()

    product_creator = ProductCreator(product_repository=product_repo)
    customer_creator = CustomerCreator(customer_repository=customer_repo)
    order_creator = OrderCreator(order_repository=order_repo)

    data_processor = DataProcessor(
        product_creator=product_creator,
        customer_creator=customer_creator,
        order_creator=order_creator,
    )

    raw_data = {
        "customer": {"first_name": "Alice", "last_name": "Wonderland"},
        "product": {"name": "Teapot", "price": 25.00},
    }
    data_processor.process_raw_data(raw_data)


if __name__ == "__main__":
    main()
