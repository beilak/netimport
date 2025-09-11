import datetime

from big_example.repo.customer_repo import CustomerRepository
from big_example.repo.order_repo import OrderRepository
from big_example.repo.product_repo import ProductRepository
from big_example.service.customer_creator import CustomerCreator
from big_example.service.order_creator import OrderCreator
from big_example.service.product_creator import ProductCreator


def main() -> None:
    """Main function to demonstrate creating some objects."""
    # Create a customer
    customer_repo = CustomerRepository()
    customer_creator = CustomerCreator(customer_repository=customer_repo)
    customer = customer_creator.new(
        first_name="John", last_name="Doe", email="john.doe@example.com", phone="123-456-7890", address_id=1
    )

    # Create a product
    product_repo = ProductRepository()
    product_creator = ProductCreator(product_repository=product_repo)
    product_creator.new(name="Laptop", description="A powerful laptop", price=1200.00, category_id=1)

    # Create an order
    order_repo = OrderRepository()
    order_creator = OrderCreator(order_repository=order_repo)
    order_creator.new(
        customer_id=customer.id, order_date=datetime.date.today(), status="pending", order_item_ids=[1, 2]
    )


if __name__ == "__main__":
    main()
