import datetime
from dataclasses import dataclass

from good_big_example.repo import CustomerRepository, OrderRepository, ProductRepository
from good_big_example.service import CustomerCreator, OrderCreator, ProductCreator


@dataclass(frozen=True, slots=True)
class CreationWorkflow:
    customer_creator: CustomerCreator
    product_creator: ProductCreator
    order_creator: OrderCreator


def build_creation_workflow() -> CreationWorkflow:
    return CreationWorkflow(
        customer_creator=CustomerCreator(customer_repository=CustomerRepository()),
        product_creator=ProductCreator(product_repository=ProductRepository()),
        order_creator=OrderCreator(order_repository=OrderRepository()),
    )


def run_demo() -> None:
    workflow = build_creation_workflow()
    customer = workflow.customer_creator.new(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="123-456-7890",
        address_id=1,
    )
    workflow.product_creator.new(
        name="Laptop",
        description="A powerful laptop",
        price=1200.00,
        category_id=1,
    )
    workflow.order_creator.new(
        customer_id=customer.id,
        order_date=datetime.date(2026, 1, 1),
        status="pending",
        order_item_ids=[1, 2],
    )
