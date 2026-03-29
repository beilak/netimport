from good_big_example.application import CreationWorkflow, build_creation_workflow


class DataProcessor:
    def __init__(self, workflow: CreationWorkflow) -> None:
        self.workflow = workflow

    def process_raw_data(self, raw_data: dict) -> None:
        if "customer" in raw_data:
            customer = raw_data["customer"]
            self.workflow.customer_creator.new(
                first_name=customer["first_name"],
                last_name=customer["last_name"],
                email=customer["email"],
                phone=customer["phone"],
                address_id=customer["address_id"],
            )
        if "product" in raw_data:
            product = raw_data["product"]
            self.workflow.product_creator.new(
                name=product["name"],
                description=product["description"],
                price=product["price"],
                category_id=product["category_id"],
            )


def main() -> None:
    data_processor = DataProcessor(workflow=build_creation_workflow())

    raw_data = {
        "customer": {
            "first_name": "Alice",
            "last_name": "Wonderland",
            "email": "alice@example.com",
            "phone": "555-0000",
            "address_id": 1,
        },
        "product": {
            "name": "Teapot",
            "description": "A compact teapot for demos",
            "price": 25.00,
            "category_id": 1,
        },
    }
    data_processor.process_raw_data(raw_data)


if __name__ == "__main__":
    main()
