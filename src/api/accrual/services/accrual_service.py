from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select
from datetime import date, datetime
import calendar
from src.api.accrual.models.accrual import AccrualPeriod, AccrualClassDistribution, AccrualStatus
from src.api.accrual.schemas.accrual import AccrualPeriodCreate, AccrualClassDistributionCreate
from src.api.services.models.service import Service, ServiceEnrollment, ServiceStatus
from src.api.invoices.models.invoice import Invoice, InvoiceAccrual


class AccrualService:
    def __init__(self, db: Session):
        self.db = db

    def create_accrual_period(self, period_data: AccrualPeriodCreate) -> AccrualPeriod:
        """Create a new accrual period"""
        period = AccrualPeriod(
            year=period_data.year,
            month=period_data.month,
            status=period_data.status
        )

        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def get_accrual_period(self, period_id: int) -> Optional[AccrualPeriod]:
        """Get an accrual period by ID"""
        return self.db.get(AccrualPeriod, period_id)

    def get_accrual_period_by_month_year(self, year: int, month: int) -> Optional[AccrualPeriod]:
        """Get an accrual period by month and year"""
        return self.db.exec(
            select(AccrualPeriod)
            .where(AccrualPeriod.year == year)
            .where(AccrualPeriod.month == month)
        ).first()

    def get_accrual_periods(self, skip: int = 0, limit: int = 100) -> List[AccrualPeriod]:
        """Get a list of accrual periods"""
        return self.db.exec(select(AccrualPeriod).offset(skip).limit(limit)).all()

    def mark_period_as_processed(self, period_id: int) -> Optional[AccrualPeriod]:
        """Mark an accrual period as processed"""
        period = self.db.get(AccrualPeriod, period_id)
        if not period:
            return None

        period.status = AccrualStatus.PROCESSED
        period.processed_at = datetime.now(timezone.utc)()

        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def create_class_distribution(self, distribution_data: AccrualClassDistributionCreate) -> AccrualClassDistribution:
        """Create a new class distribution for a service in a specific month"""
        distribution = AccrualClassDistribution(
            service_id=distribution_data.service_id,
            year=distribution_data.year,
            month=distribution_data.month,
            num_classes=distribution_data.num_classes,
            percentage=distribution_data.percentage
        )

        self.db.add(distribution)
        self.db.commit()
        self.db.refresh(distribution)
        return distribution

    def get_class_distributions_by_service(self, service_id: int) -> List[AccrualClassDistribution]:
        """Get all class distributions for a service"""
        return self.db.exec(
            select(AccrualClassDistribution)
            .where(AccrualClassDistribution.service_id == service_id)
        ).all()

    def get_class_distributions_by_month_year(self, year: int, month: int) -> List[AccrualClassDistribution]:
        """Get all class distributions for a specific month and year"""
        return self.db.exec(
            select(AccrualClassDistribution)
            .where(AccrualClassDistribution.year == year)
            .where(AccrualClassDistribution.month == month)
        ).all()

    def calculate_class_distribution(self, service_id: int) -> List[AccrualClassDistribution]:
        """
        Calculate the distribution of classes per month for a service
        and create AccrualClassDistribution records
        """
        service = self.db.get(Service, service_id)
        if not service:
            return []

        # Parse class days
        class_days = [day.strip() for day in service.class_days.split(",")]

        # Map day names to weekday numbers (0 = Monday, 6 = Sunday)
        day_map = {
            "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6
        }

        weekdays = [day_map[day] for day in class_days if day in day_map]

        # Calculate classes per month
        start_date = service.start_date
        end_date = service.end_date

        current_year = start_date.year
        current_month = start_date.month

        distributions = []
        total_classes = 0

        while (current_year < end_date.year or
               (current_year == end_date.year and current_month <= end_date.month)):

            # Get the number of days in the month
            _, days_in_month = calendar.monthrange(current_year, current_month)

            # Calculate the first and last day to consider in this month
            if current_year == start_date.year and current_month == start_date.month:
                first_day = start_date.day
            else:
                first_day = 1

            if current_year == end_date.year and current_month == end_date.month:
                last_day = end_date.day
            else:
                last_day = days_in_month

            # Count classes in this month
            classes_in_month = 0
            for day in range(first_day, last_day + 1):
                current_date = date(current_year, current_month, day)
                if current_date.weekday() in weekdays:
                    classes_in_month += 1

            total_classes += classes_in_month

            # Move to the next month
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1

        # Now calculate percentages and create distributions
        current_year = start_date.year
        current_month = start_date.month

        while (current_year < end_date.year or
               (current_year == end_date.year and current_month <= end_date.month)):

            # Get the number of days in the month
            _, days_in_month = calendar.monthrange(current_year, current_month)

            # Calculate the first and last day to consider in this month
            if current_year == start_date.year and current_month == start_date.month:
                first_day = start_date.day
            else:
                first_day = 1

            if current_year == end_date.year and current_month == end_date.month:
                last_day = end_date.day
            else:
                last_day = days_in_month

            # Count classes in this month
            classes_in_month = 0
            for day in range(first_day, last_day + 1):
                current_date = date(current_year, current_month, day)
                if current_date.weekday() in weekdays:
                    classes_in_month += 1

            # Calculate percentage
            percentage = classes_in_month / \
                service.total_classes if service.total_classes > 0 else 0

            # Create distribution
            distribution_data = AccrualClassDistributionCreate(
                service_id=service_id,
                year=current_year,
                month=current_month,
                num_classes=classes_in_month,
                percentage=percentage
            )

            distribution = self.create_class_distribution(distribution_data)
            distributions.append(distribution)

            # Move to the next month
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1

        return distributions

    def process_accruals_for_period(self, year: int, month: int) -> Tuple[int, List[str]]:
        """
        Process accruals for a specific period (month/year)

        Returns:
            Tuple containing the number of accruals created and a list of error messages
        """
        # Get or create the accrual period
        period = self.get_accrual_period_by_month_year(year, month)
        if not period:
            period_data = AccrualPeriodCreate(year=year, month=month)
            period = self.create_accrual_period(period_data)

        # Check if the period is already processed
        if period.status == AccrualStatus.PROCESSED:
            return 0, ["Period is already processed"]

        # Get all services that are active in this period
        services = self.db.exec(select(Service)).all()
        active_services = []

        for service in services:
            # Check if the service is active in this period
            period_start = date(year, month, 1)
            if month == 12:
                period_end = date(year + 1, 1, 1)
            else:
                period_end = date(year, month + 1, 1)

            if (service.start_date < period_end and service.end_date >= period_start):
                active_services.append(service)

        # Process accruals for each active service
        accruals_created = 0
        errors = []

        for service in active_services:
            # Get class distribution for this service in this period
            distribution = self.db.exec(
                select(AccrualClassDistribution)
                .where(AccrualClassDistribution.service_id == service.id)
                .where(AccrualClassDistribution.year == year)
                .where(AccrualClassDistribution.month == month)
            ).first()

            if not distribution:
                # Calculate distribution if it doesn't exist
                distributions = self.calculate_class_distribution(service.id)
                for dist in distributions:
                    if dist.year == year and dist.month == month:
                        distribution = dist
                        break

            if not distribution:
                errors.append(
                    f"Could not calculate class distribution for service {service.id}")
                continue

            # Get all enrollments for this service
            enrollments = self.db.exec(
                select(ServiceEnrollment)
                .where(ServiceEnrollment.service_id == service.id)
            ).all()

            for enrollment in enrollments:
                # Check if the enrollment is active in this period
                is_active = False

                if enrollment.status == ServiceStatus.ACTIVE:
                    is_active = True
                elif enrollment.status == ServiceStatus.POSTPONED and enrollment.postponed_date:
                    # Check if postponed during this period
                    period_start = date(year, month, 1)
                    if month == 12:
                        period_end = date(year + 1, 1, 1)
                    else:
                        period_end = date(year, month + 1, 1)

                    if enrollment.postponed_date >= period_start and enrollment.postponed_date < period_end:
                        # Accrual until postponed date
                        is_active = True
                elif enrollment.status == ServiceStatus.DROPPED and enrollment.dropped_date:
                    # Check if dropped during this period
                    period_start = date(year, month, 1)
                    if month == 12:
                        period_end = date(year + 1, 1, 1)
                    else:
                        period_end = date(year, month + 1, 1)

                    if enrollment.dropped_date >= period_start and enrollment.dropped_date < period_end:
                        # Accrue remaining amount
                        is_active = True

                if not is_active:
                    continue

                # Get invoices for this client
                client_id = enrollment.client_id
                invoices = self.db.exec(
                    select(Invoice)
                    .where(Invoice.client_id == client_id)
                ).all()

                for invoice in invoices:
                    # Check if this invoice is related to this service
                    # In a real implementation, you would have a more robust way to link invoices to services

                    # Create accrual for this invoice
                    accrual_date = date(year, month, 1)

                    # Calculate amount based on distribution percentage
                    amount = invoice.total_amount * distribution.percentage

                    # Check if this is a special case (dropped or postponed)
                    if enrollment.status == ServiceStatus.DROPPED and enrollment.dropped_date:
                        period_start = date(year, month, 1)
                        if month == 12:
                            period_end = date(year + 1, 1, 1)
                        else:
                            period_end = date(year, month + 1, 1)

                        if enrollment.dropped_date >= period_start and enrollment.dropped_date < period_end:
                            # Accrue remaining amount
                            # Get all existing accruals for this invoice
                            existing_accruals = self.db.exec(
                                select(InvoiceAccrual)
                                .where(InvoiceAccrual.invoice_id == invoice.id)
                            ).all()

                            total_accrued = sum(
                                accrual.amount for accrual in existing_accruals)
                            remaining = invoice.total_amount - total_accrued

                            if remaining > 0:
                                amount = remaining

                    # Create the accrual
                    accrual = InvoiceAccrual(
                        invoice_id=invoice.id,
                        service_id=service.id,
                        accrual_date=accrual_date,
                        amount=amount,
                        percentage=distribution.percentage,
                        status="pending"
                    )

                    self.db.add(accrual)
                    accruals_created += 1

        # Commit all changes
        self.db.commit()

        # Mark period as processed
        period.status = AccrualStatus.PROCESSED
        period.processed_at = datetime.now(timezone.utc)()
        self.db.add(period)
        self.db.commit()

        return accruals_created, errors
