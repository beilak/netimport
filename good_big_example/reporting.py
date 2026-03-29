from dataclasses import dataclass

from good_big_example.repo import CustomerRepository, OrderRepository, ProductRepository


@dataclass(frozen=True, slots=True)
class RepositoryBundle:
    product_repo: ProductRepository
    order_repo: OrderRepository
    customer_repo: CustomerRepository


def build_repository_bundle() -> RepositoryBundle:
    return RepositoryBundle(
        product_repo=ProductRepository(),
        order_repo=OrderRepository(),
        customer_repo=CustomerRepository(),
    )


class SalesReportService:
    def __init__(self, repositories: RepositoryBundle) -> None:
        self.repositories = repositories

    def generate_sales_report(self) -> str:
        report = "Sales Report\n"
        report += "============\n"
        report += "Products: 10\n"
        report += "Orders: 5\n"
        report += "Customers: 3\n"
        return report


def build_sales_report_service() -> SalesReportService:
    return SalesReportService(repositories=build_repository_bundle())
