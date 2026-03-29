from good_big_example.reporting import SalesReportService, build_sales_report_service


class ReportGenerator:
    def __init__(self, report_service: SalesReportService) -> None:
        self.report_service = report_service

    def generate_sales_report(self) -> str:
        return self.report_service.generate_sales_report()


def main() -> None:
    report_generator = ReportGenerator(report_service=build_sales_report_service())

    report_generator.generate_sales_report()


if __name__ == "__main__":
    main()
