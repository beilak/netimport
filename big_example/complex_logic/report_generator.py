from big_example.repo.customer_repo import CustomerRepository
from big_example.repo.order_repo import OrderRepository
from big_example.repo.product_repo import ProductRepository


class ReportGenerator:
    def __init__(
        self,
        product_repo: ProductRepository,
        order_repo: OrderRepository,
        customer_repo: CustomerRepository,
    ) -> None:
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.customer_repo = customer_repo

    def generate_sales_report(self) -> str:
        # In a real app, this would fetch data from the repos
        # and generate a report.
        report = "Sales Report\\n"
        report += "============\\n"
        report += "Products: 10\\n"  # dummy data
        report += "Orders: 5\\n"  # dummy data
        report += "Customers: 3\\n"  # dummy data
        return report


def main() -> None:
    product_repo = ProductRepository()
    order_repo = OrderRepository()
    customer_repo = CustomerRepository()

    report_generator = ReportGenerator(
        product_repo=product_repo,
        order_repo=order_repo,
        customer_repo=customer_repo,
    )

    report_generator.generate_sales_report()


if __name__ == "__main__":
    main()
