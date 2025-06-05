from datetime import date
from typing import List, Dict, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, or_, not_, exists
from sqlalchemy.orm import aliased
from fastapi.logger import logger

from src.api.services.models.service_contract import ServiceContract
from src.api.accruals.models.contract_accrual import ContractAccrual
from src.api.services.models.service_period import ServicePeriod
from src.api.accruals.models.accrued_period import AccruedPeriod
from src.api.common.constants.services import ServiceContractStatus, ServicePeriodStatus, map_educational_status
from src.api.accruals.constants.accruals import ContractAccrualStatus
from src.api.accruals.schemas import ContractProcessingResult, ProcessingStatus, SyncActionSummary, SyncActionDetail
from src.api.common.utils.datetime import get_month_boundaries, get_month_start, get_month_end
from src.api.integrations.notion.utils import is_educational_status_ended, is_educational_status_dropped, get_client_educational_data


class ContractAccrualProcessor:
    """
    Service to process contract accruals following the business logic schema.

    This service implements the decision tree from accrual-process-schema.yaml
    handling different ServiceContract statuses and their corresponding accrual logic.
    """

    def __init__(self, db: Session):
        self.db = db
        self.notifications: List[Dict] = []

    async def process_all_contracts(self, target_month: date) -> Dict:
        """
        Process all ServiceContracts according to the accrual schema.

        Args:
            target_month: The month to process accruals for

        Returns:
            Dictionary with processing results and statistics
        """
        print('target_month', target_month)
        logger.info(
            f"Starting contract accrual processing for month: {target_month}")

        # Get all ServiceContracts
        contracts = self._get_all_accruable_service_contracts(target_month)
        print('contracts', contracts)

        results = []
        stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

        for contract in contracts:
            print('contract', contract)
            try:
                result = await self._process_contract(contract, target_month)
                results.append(result)
                stats['total_processed'] += 1

                if result.status == ProcessingStatus.SUCCESS:
                    stats['successful'] += 1
                elif result.status == ProcessingStatus.FAILED:
                    stats['failed'] += 1
                else:
                    stats['skipped'] += 1

            except Exception as e:
                print('e', e)
                logger.error(
                    f"Error processing contract {contract.id}: {str(e)}")
                error_result = ContractProcessingResult(
                    contract_id=contract.id,
                    status=ProcessingStatus.FAILED,
                    message=f"Processing error: {str(e)}"
                )
                results.append(error_result)
                stats['failed'] += 1
                stats['total_processed'] += 1

        return {
            'results': results,
            'notifications': self.notifications,
            **stats
        }

    def _get_all_accruable_service_contracts(self, target_month: date) -> List[ServiceContract]:
        """
        Get ServiceContracts that need processing for the target month.

        Filters out contracts that don't need processing:
        - Contracts that have not started on or before the target month
        - Contracts with ServicePeriods that don't overlap with target month
        - Contracts that are CLOSED/CANCELED with COMPLETED accruals
        """
        # Calculate month boundaries
        month_start, month_end = get_month_boundaries(target_month)

        print('month_start', month_start)
        print('month_end', month_end)

        # Create aliases for subqueries
        ServicePeriodAlias = aliased(ServicePeriod)
        ContractAccrualAlias = aliased(ContractAccrual)

        # Base query with eager loading
        stmt = (
            select(ServiceContract)
            .options(
                selectinload(ServiceContract.client),
                selectinload(ServiceContract.service),
                selectinload(ServiceContract.contract_accrual),
                selectinload(ServiceContract.periods),
                selectinload(ServiceContract.invoices)
            )
        )

        # Filter 0: Exclude contracts that haven't started yet (contract_date > target month end)
        exclude_not_started = ServiceContract.contract_date > month_end

        # Filter 1: Exclude contracts where status is CLOSED/CANCELED AND accrual is COMPLETED
        # EXCEPTION: Include zero-amount contracts only if they haven't been processed yet
        exclude_completed = and_(
            ServiceContract.status.in_(
                [ServiceContractStatus.CLOSED, ServiceContractStatus.CANCELED]),
            exists().where(
                and_(
                    ContractAccrualAlias.contract_id == ServiceContract.id,
                    ContractAccrualAlias.accrual_status == ContractAccrualStatus.COMPLETED
                )
            ),
            # IMPORTANT: Only exclude zero-amount contracts if they already have AccruedPeriod records
            or_(
                # Non-zero contracts: exclude when completed
                ServiceContract.contract_amount != 0,
                exists().where(  # Zero-amount contracts: exclude only if they have AccruedPeriod records
                    and_(
                        ContractAccrualAlias.contract_id == ServiceContract.id,
                        exists().where(
                            AccruedPeriod.contract_accrual_id == ContractAccrualAlias.id
                        )
                    )
                )
            )
        )

        # Filter 2: Exclude contracts with ServicePeriods that don't overlap with target month
        # BUT only for ACTIVE contracts - CANCELED/CLOSED contracts should be processed regardless
        # A contract has overlapping periods if ANY period overlaps with the month
        has_overlapping_periods = exists().where(
            and_(
                ServicePeriodAlias.contract_id == ServiceContract.id,
                ServicePeriodAlias.start_date <= month_end,
                ServicePeriodAlias.end_date >= month_start
            )
        )

        # Exclude ACTIVE contracts that have periods but none overlap with target month
        # Don't exclude CANCELED/CLOSED contracts as they may need final processing
        exclude_non_overlapping = and_(
            # Only apply to ACTIVE contracts
            ServiceContract.status == ServiceContractStatus.ACTIVE,
            exists().where(ServicePeriodAlias.contract_id == ServiceContract.id),  # Has periods
            not_(has_overlapping_periods)  # But none overlap
        )

        # Apply filters: exclude all three conditions
        stmt = stmt.where(
            not_(or_(exclude_not_started, exclude_completed, exclude_non_overlapping))
        )

        contracts = self.db.execute(stmt).scalars().all()
        print('filtered_contracts_count', len(contracts))

        return contracts

    async def _process_contract(self, contract: ServiceContract, target_month: date) -> ContractProcessingResult:
        """
        Process a single ServiceContract following the accrual schema logic.

        Args:
            contract: ServiceContract to process
            target_month: Target month for accrual processing

        Returns:
            ContractProcessingResult with processing outcome
        """
        print('contract.status', contract.status)

        if contract.status == ServiceContractStatus.ACTIVE:
            return await self._process_active_contract(contract, target_month)
        elif contract.status == ServiceContractStatus.CANCELED:
            return await self._process_canceled_contract(contract, target_month)
        elif contract.status == ServiceContractStatus.CLOSED:
            return await self._process_closed_contract(contract, target_month)
        else:
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SKIPPED,
                message=f"Unknown contract status: {contract.status}"
            )

    async def _process_active_contract(self, contract: ServiceContract, target_month: date) -> ContractProcessingResult:
        """Process ServiceContract with ACTIVE status."""
        contract_accrual = self._get_or_create_contract_accrual(contract)
        print('contract_accrual', contract_accrual)

        # Check if accrual is completed or has nothing left to accrue
        if contract_accrual.accrual_status == ContractAccrualStatus.COMPLETED:
            return self._handle_completed_accrual(contract, contract_accrual)

        # Special case: Zero-amount contracts without service periods should be checked for resignation
        # before auto-completion, as they might need CRM processing
        service_periods = self._get_contract_service_periods(contract)
        if contract_accrual.remaining_amount_to_accrue == 0:
            if not service_periods:
                print('zero_amount_contract_without_service_periods_checking_resignation',
                      contract_accrual.remaining_amount_to_accrue)
                return await self._process_contract_without_service_period(contract, contract_accrual, target_month)
            # Auto-complete if remaining amount is exactly 0 (but process negative amounts)
            return self._handle_zero_amount_completion(contract, contract_accrual, "active_contract")

        # If remaining amount is negative, accrue the loss fully
        if contract_accrual.remaining_amount_to_accrue < 0:
            return self._handle_negative_amount_accrual(contract, contract_accrual, target_month, "loss_overpayment")

        if not service_periods:
            return await self._process_contract_without_service_period(contract, contract_accrual, target_month)
        else:
            return await self._process_contract_with_service_periods(contract, contract_accrual, service_periods, target_month)

    async def _process_canceled_contract(self, contract: ServiceContract, target_month: date) -> ContractProcessingResult:
        """Process ServiceContract with CANCELED status."""
        contract_accrual = self._get_or_create_contract_accrual(contract)

        if contract_accrual.accrual_status == ContractAccrualStatus.COMPLETED:
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SKIPPED,
                message="Contract accrual already completed"
            )

        service_periods = self._get_contract_service_periods(contract)
        # Special case: Zero-amount contracts without service periods should be checked for resignation
        # before auto-completion, as they might need CRM processing
        if contract_accrual.remaining_amount_to_accrue == 0:
            if not service_periods:
                print('zero_amount_canceled_contract_without_service_periods_checking_resignation',
                      contract_accrual.remaining_amount_to_accrue)
                return await self._process_canceled_without_service_period(contract, contract_accrual, target_month)
            # Auto-complete if remaining amount is exactly 0 (but process negative amounts)
            return self._handle_zero_amount_completion(contract, contract_accrual, "canceled_contract")

        # If remaining amount is negative, accrue the loss fully
        if contract_accrual.remaining_amount_to_accrue < 0:
            return self._handle_negative_amount_accrual(contract, contract_accrual, target_month, "canceled_contract_loss_overpayment")

        if not service_periods:
            return await self._process_canceled_without_service_period(contract, contract_accrual, target_month)
        else:
            return self._process_canceled_with_service_periods(contract, contract_accrual, service_periods, target_month)

    async def _process_closed_contract(self, contract: ServiceContract, target_month: date) -> ContractProcessingResult:
        """Process ServiceContract with CLOSED status."""
        contract_accrual = self._get_or_create_contract_accrual(contract)

        if contract_accrual.accrual_status == ContractAccrualStatus.COMPLETED:
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SKIPPED,
                message="Contract accrual already completed"
            )

        # Auto-complete if remaining amount is exactly 0 (but process negative amounts)
        if contract_accrual.remaining_amount_to_accrue == 0:
            return self._handle_zero_amount_completion(contract, contract_accrual, "closed_contract")

        # If remaining amount is negative, accrue the loss fully
        if contract_accrual.remaining_amount_to_accrue < 0:
            return self._handle_negative_amount_accrual(contract, contract_accrual, target_month, "closed_contract_loss_overpayment")

        service_periods = self._get_contract_service_periods(contract)

        if not service_periods:
            return await self._process_closed_without_service_period(contract, contract_accrual, target_month)
        else:
            return self._process_closed_with_service_periods(contract, contract_accrual, service_periods, target_month)

    async def _process_contract_without_service_period(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date) -> ContractProcessingResult:
        """Handle contracts without ServicePeriods - check Notion integration."""
        # Check if client found in Notion
        external_client_data = await get_client_educational_data(contract.client)

        if not external_client_data:
            if self._is_contract_recent(contract.contract_date):
                # Client probably missing - check contract date
                self._add_notification("not_congruent_status",
                                       f"Contract {contract.id} - Possibly a client missing in CRM")
                return ContractProcessingResult(
                    contract_id=contract.id,
                    status=ProcessingStatus.SKIPPED,
                    message="Recent contract without Notion data - possibly missing in CRM"
                )
            else:
                # Contract resigned - handle based on amount type
                if contract_accrual.remaining_amount_to_accrue == 0:
                    # Zero-amount contract resignation
                    context = "resignation (>15 days, no Notion profile)"
                    return self._handle_zero_amount_contract_resignation(contract, contract_accrual, context, target_month)
                else:
                    # Non-zero amount contract resignation (existing logic)
                    is_negative = contract_accrual.remaining_amount_to_accrue < 0
                    context = "contract resignation (>15 days, no Notion profile)"
                    return self._handle_contract_resignation(contract, contract_accrual, target_month, context, is_negative)
        else:
            # Found in Notion - check educational status
            educational_status = map_educational_status(
                external_client_data.get('educational_status'))

            is_ended = is_educational_status_ended(educational_status)

            if is_ended:
                # Check status change date overlap
                status_change_date = external_client_data.get(
                    'status_change_date')
                if self._is_status_change_before_month_end(status_change_date, target_month):
                    # Handle based on amount type
                    if contract_accrual.remaining_amount_to_accrue == 0:
                        # Zero-amount contract with ended educational status
                        context = "ended educational status"
                        return self._handle_zero_amount_contract_resignation(contract, contract_accrual, context, target_month)
                    else:
                        # Non-zero amount contract with ended educational status (existing logic)
                        return self._handle_educational_status_accrual(contract, contract_accrual, target_month, educational_status)
                else:
                    return ContractProcessingResult(
                        contract_id=contract.id,
                        status=ProcessingStatus.SKIPPED,
                        message="Status change date after month end - ignoring"
                    )
            else:
                if self._is_contract_recent(contract.contract_date):
                    return ContractProcessingResult(
                        contract_id=contract.id,
                        status=ProcessingStatus.SKIPPED,
                        message="Recent contract without service period - ignoring"
                    )
                else:
                    self._add_notification("not_congruent_status",
                                           f"Contract {contract.id} - Client without service period in CRM")
                    return ContractProcessingResult(
                        contract_id=contract.id,
                        status=ProcessingStatus.SKIPPED,
                        message="Contract without service period - reminder sent"
                    )

    async def _process_contract_with_service_periods(self, contract: ServiceContract, contract_accrual: ContractAccrual, service_periods: List[ServicePeriod], target_month: date) -> ContractProcessingResult:
        """Handle contracts with ServicePeriods."""
        # Find the service period that overlaps with target month
        overlapping_period = self._find_overlapping_period(
            service_periods, target_month)

        if not overlapping_period:
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SKIPPED,
                message="No service period overlaps with target month"
            )

        if self._is_status_change_before_month_end(overlapping_period.status_change_date, target_month):
            if overlapping_period.status == ServicePeriodStatus.POSTPONED:
                return self._process_postponed_service_period(contract, contract_accrual, overlapping_period, target_month)
            elif overlapping_period.status == ServicePeriodStatus.DROPPED:
                return self._process_dropped_service_period(contract, contract_accrual, overlapping_period, target_month)
            elif overlapping_period.status == ServicePeriodStatus.ENDED:
                return self._process_ended_service_period(contract, contract_accrual, overlapping_period, target_month)
        # Special case: ENDED/DROPPED periods with status_change_date after end_date
        # These should be fully accrued in the last month of the service period
        if self._is_period_naturally_completed(overlapping_period, target_month):
            if overlapping_period.status == ServicePeriodStatus.ENDED:
                return self._process_ended_service_period(contract, contract_accrual, overlapping_period, target_month)
            elif overlapping_period.status == ServicePeriodStatus.DROPPED:
                return self._process_dropped_service_period(contract, contract_accrual, overlapping_period, target_month)
        # If no special case, process normally
        return self._process_active_service_period(contract, contract_accrual, overlapping_period, target_month)

    def _process_active_service_period(self, contract: ServiceContract, contract_accrual: ContractAccrual, period: ServicePeriod, target_month: date) -> ContractProcessingResult:
        """Process ACTIVE service period - accrue respective portion."""
        portion = self._calculate_monthly_portion(
            contract_accrual, period, target_month)
        accrued_amount = self._accrue_portion(
            contract, contract_accrual, portion, target_month, period)

        return ContractProcessingResult(
            contract_id=contract.id,
            service_period_id=period.id,
            status=ProcessingStatus.SUCCESS,
            message=f"Accrued portion {portion:.2%} - Amount: {accrued_amount:.2f}"
        )

    def _process_postponed_service_period(self, contract: ServiceContract, contract_accrual: ContractAccrual, period: ServicePeriod, target_month: date) -> ContractProcessingResult:
        """Process POSTPONED service period - accrue until status change date."""
        # Accrue normally until status change date
        portion = self._calculate_portion_until_status_change(
            contract_accrual, period, target_month)
        accrued_amount = self._accrue_portion(
            contract, contract_accrual, portion, target_month, period)

        # Update contract accrual to PAUSED if currently ACTIVE
        if contract_accrual.accrual_status == ContractAccrualStatus.ACTIVE:
            self._update_contract_accrual_status(
                contract_accrual, ContractAccrualStatus.PAUSED)

        return ContractProcessingResult(
            contract_id=contract.id,
            service_period_id=period.id,
            status=ProcessingStatus.SUCCESS,
            message=f"Accrued until postponement - Amount: {accrued_amount:.2f}, Status: PAUSED"
        )

    def _process_dropped_service_period(self, contract: ServiceContract, contract_accrual: ContractAccrual, period: ServicePeriod, target_month: date) -> ContractProcessingResult:
        """Process DROPPED service period - accrue fully on status change date."""
        # Special case: If contract amount is negative and this is the first accrual (no previous accruals)
        # This handles the case where service period was dropped before accrued period
        if (contract_accrual.remaining_amount_to_accrue < 0 and
                contract_accrual.total_amount_accrued == 0):
            return self._handle_negative_amount_accrual(
                contract,
                contract_accrual,
                target_month,
                "service_period_dropped_before_accrual",
                service_period_id=period.id
            )

        # Normal case: accrue fully for dropped service period
        return self._handle_full_accrual_with_status_update(
            contract,
            contract_accrual,
            target_month,
            ServiceContractStatus.CANCELED,
            "Service period dropped - accrued fully and contract canceled",
            service_period_id=period.id
        )

    def _process_ended_service_period(self, contract: ServiceContract, contract_accrual: ContractAccrual, period: ServicePeriod, target_month: date) -> ContractProcessingResult:
        """Process ENDED service period - accrue remaining amount."""
        remaining_amount = contract_accrual.remaining_amount_to_accrue
        return self._handle_full_accrual_with_status_update(
            contract,
            contract_accrual,
            target_month,
            ServiceContractStatus.CLOSED,
            f"Service period ended - accrued remaining amount: {remaining_amount:.2f}, contract closed",
            service_period_id=period.id
        )

    async def _process_canceled_without_service_period(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date) -> ContractProcessingResult:
        """Handle canceled contracts without ServicePeriods."""
        external_client_data = await get_client_educational_data(contract.client)

        if not external_client_data:
            # Contract resigned - handle based on amount type
            if contract_accrual.remaining_amount_to_accrue == 0:
                # Zero-amount canceled contract resignation
                context = "canceled contract resignation"
                return self._handle_zero_amount_contract_resignation(contract, contract_accrual, context, target_month)
            else:
                # Non-zero amount canceled contract resignation (existing logic)
                is_negative = contract_accrual.remaining_amount_to_accrue < 0
                context = "canceled contract resigned"
                return self._handle_contract_resignation(contract, contract_accrual, target_month, context, is_negative)
        else:
            educational_status = map_educational_status(
                external_client_data.get('educational_status'))

            # Treat DROPPED as resignation case instead of requiring ended status
            if is_educational_status_dropped(educational_status):
                # Handle dropped status as resignation - based on amount type
                if contract_accrual.remaining_amount_to_accrue == 0:
                    # Zero-amount canceled contract with dropped status
                    context = "canceled contract with dropped status"
                    return self._handle_zero_amount_contract_resignation(contract, contract_accrual, context, target_month)
                else:
                    # Non-zero amount canceled contract with dropped status
                    is_negative = contract_accrual.remaining_amount_to_accrue < 0
                    context = "canceled contract with dropped status"
                    return self._handle_contract_resignation(contract, contract_accrual, target_month, context, is_negative)
            elif is_educational_status_ended(educational_status):
                # Handle based on amount type
                if contract_accrual.remaining_amount_to_accrue == 0:
                    # Zero-amount canceled contract with ended status
                    context = "canceled contract with ended status"
                    return self._handle_zero_amount_contract_resignation(contract, contract_accrual, context, target_month)
                else:
                    # Non-zero amount canceled contract with ended status (existing logic)
                    return self._handle_full_accrual_with_status_update(
                        contract,
                        contract_accrual,
                        target_month,
                        ServiceContractStatus.CLOSED,
                        "Canceled contract with ended status - accrued fully and closed"
                    )
            else:
                self._add_notification("not_congruent_status",
                                       f"Canceled contract {contract.id} but client doesn't have ended or dropped status")
                return ContractProcessingResult(
                    contract_id=contract.id,
                    status=ProcessingStatus.SKIPPED,
                    message="Not congruent status - notification sent"
                )

    def _process_canceled_with_service_periods(self, contract: ServiceContract, contract_accrual: ContractAccrual, service_periods: List[ServicePeriod], target_month: date) -> ContractProcessingResult:
        """Handle canceled contracts with ServicePeriods."""
        # Check service period statuses
        active_or_ended = any(p.status in [
                              ServicePeriodStatus.ACTIVE, ServicePeriodStatus.ENDED] for p in service_periods)

        if active_or_ended:
            self._add_notification("not_congruent_status",
                                   f"Contract {contract.id} canceled but client doesn't have DROPPED service periods")
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SKIPPED,
                message="Contract canceled but has active/ended service periods"
            )
        else:
            # Has DROPPED or POSTPONED periods
            return self._handle_full_accrual_with_status_update(
                contract,
                contract_accrual,
                target_month,
                ServiceContractStatus.CANCELED,
                "Canceled contract with dropped/postponed periods - accrued fully"
            )

    async def _process_closed_without_service_period(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date) -> ContractProcessingResult:
        """Handle closed contracts without ServicePeriods."""
        external_client_data = await get_client_educational_data(contract.client)

        if not external_client_data:
            self._add_notification("not_congruent_status",
                                   f"Contract {contract.id} closed but client doesn't have service periods")
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SKIPPED,
                message="Closed contract without service periods - notification sent"
            )
        else:
            educational_status = map_educational_status(
                external_client_data.get('educational_status'))
            if is_educational_status_ended(educational_status):
                return self._handle_full_accrual_with_status_update(
                    contract,
                    contract_accrual,
                    target_month,
                    ServiceContractStatus.CLOSED,
                    "Closed contract with ended status - accrued fully"
                )
            else:
                self._add_notification("not_congruent_status",
                                       f"Contract {contract.id} closed but client doesn't have ENDED service periods")
                return ContractProcessingResult(
                    contract_id=contract.id,
                    status=ProcessingStatus.SKIPPED,
                    message="Not congruent status - notification sent"
                )

    def _process_closed_with_service_periods(self, contract: ServiceContract, contract_accrual: ContractAccrual, service_periods: List[ServicePeriod], target_month: date) -> ContractProcessingResult:
        """Handle closed contracts with ServicePeriods."""
        # Check if all service periods are ENDED
        non_ended_periods = [
            p for p in service_periods if p.status != ServicePeriodStatus.ENDED]

        if non_ended_periods:
            self._add_notification("not_congruent_status",
                                   f"Contract {contract.id} closed but client doesn't have ENDED service periods")
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SKIPPED,
                message="Closed contract with non-ended service periods - notification sent"
            )
        else:
            return self._handle_full_accrual_with_status_update(
                contract,
                contract_accrual,
                target_month,
                ServiceContractStatus.CLOSED,
                "Closed contract with ended periods - accrued fully"
            )

    def _get_or_create_contract_accrual(self, contract: ServiceContract) -> ContractAccrual:
        """Get existing ContractAccrual or create a new one."""
        if contract.contract_accrual:
            return contract.contract_accrual

        # Create new ContractAccrual
        contract_accrual = ContractAccrual(
            contract_id=contract.id,
            total_amount_to_accrue=contract.contract_amount,
            total_amount_accrued=0.0,
            remaining_amount_to_accrue=contract.contract_amount,
            total_sessions_to_accrue=contract.service.total_sessions if contract.service else 0,
            total_sessions_accrued=0,
            sessions_remaining_to_accrue=contract.service.total_sessions if contract.service else 0,
            accrual_status=ContractAccrualStatus.ACTIVE
        )

        self.db.add(contract_accrual)
        self.db.commit()
        self.db.refresh(contract_accrual)

        return contract_accrual

    def _get_contract_service_periods(self, contract: ServiceContract) -> List[ServicePeriod]:
        """Get all ServicePeriods for a contract."""
        return contract.periods or []

    def _handle_completed_accrual(self, contract: ServiceContract, contract_accrual: ContractAccrual) -> ContractProcessingResult:
        """Handle contracts with completed accruals."""
        # Update contract status based on total to accrue
        if contract_accrual.total_amount_to_accrue > 0:
            self._update_contract_status(
                contract, ServiceContractStatus.CLOSED)
        else:
            self._update_contract_status(
                contract, ServiceContractStatus.CANCELED)

        return ContractProcessingResult(
            contract_id=contract.id,
            status=ProcessingStatus.SKIPPED,
            message="Contract accrual completed - updated contract status"
        )

    def _is_contract_recent(self, contract_date: date) -> bool:
        """Check if contract date is within 15 days."""
        return (date.today() - contract_date).days <= 15

    def _is_status_change_before_month_end(self, change_date: Optional[date], target_month: date) -> bool:
        """Check if status change date is before end of target month."""
        if not change_date:
            return False

        # Get last day of target month
        month_end = get_month_end(target_month)

        return change_date <= month_end

    def _find_overlapping_period(self, periods: List[ServicePeriod], target_month: date) -> Optional[ServicePeriod]:
        """Find service period that overlaps with target month."""
        # Get first and last day of target month
        month_start, month_end = get_month_boundaries(target_month)

        for period in periods:
            if period.start_date <= month_end and period.end_date >= month_start:
                return period

        return None

    def _calculate_monthly_portion(self, contract_accrual: ContractAccrual, period: ServicePeriod, target_month: date) -> float:
        """
        Calculate the portion of remaining sessions that falls within target month.

        This calculates based on remaining sessions to ensure proper accrual distribution
        in final periods where only a portion of the total contract remains.
        """
        # Only return zero if exactly zero, process negative amounts
        if contract_accrual.remaining_amount_to_accrue == 0:
            print('no_remaining_amount_to_accrue_returning_zero',
                  contract_accrual.remaining_amount_to_accrue)
            return 0.0

        # Get month boundaries
        month_start, month_end = get_month_boundaries(target_month)

        # Calculate overlap
        overlap_start = max(period.start_date, month_start)
        overlap_end = min(period.end_date, month_end)

        if overlap_start > overlap_end:
            return 0.0

        # Calculate sessions in overlap
        sessions_in_overlap = period.get_sessions_between(
            overlap_start, overlap_end)

        # Use remaining sessions instead of total sessions
        remaining_sessions = contract_accrual.sessions_remaining_to_accrue
        print('remaining_sessions', remaining_sessions)
        print('sessions_in_overlap', sessions_in_overlap)

        if remaining_sessions <= 0:
            print('no_remaining_sessions_returning_zero', remaining_sessions)
            return 0.0

        # Calculate portion based on remaining sessions
        portion = min(1.0, sessions_in_overlap / remaining_sessions)
        print('calculated_portion', portion)

        return portion

    def _calculate_portion_until_status_change(self, contract_accrual: ContractAccrual, period: ServicePeriod, target_month: date) -> float:
        """Calculate portion until status change date based on remaining sessions."""
        # Only return zero if exactly zero, process negative amounts
        if contract_accrual.remaining_amount_to_accrue == 0:
            print('no_remaining_amount_for_status_change_returning_zero',
                  contract_accrual.remaining_amount_to_accrue)
            return 0.0

        if not period.status_change_date:
            return self._calculate_monthly_portion(contract_accrual, period, target_month)

        # Calculate portion until status change date
        month_start, month_end = get_month_boundaries(target_month)
        effective_end = min(period.status_change_date, month_end)

        overlap_start = max(period.start_date, month_start)

        if overlap_start > effective_end:
            return 0.0

        sessions_until_change = period.get_sessions_between(
            overlap_start, effective_end)
        remaining_sessions = contract_accrual.sessions_remaining_to_accrue

        if remaining_sessions <= 0:
            print('no_remaining_sessions_for_status_change_returning_zero',
                  remaining_sessions)
            return 0.0

        return min(1.0, sessions_until_change / remaining_sessions)

    def _accrue_portion(self, contract: ServiceContract, contract_accrual: ContractAccrual, portion: float, target_month: date, period: ServicePeriod) -> float:
        """
        Accrue a portion of the remaining contract amount.

        This now calculates the accrued amount from remaining_amount_to_accrue
        instead of the total contract amount, ensuring proper final period calculations.
        """
        # Only skip if exactly zero, process negative amounts
        if contract_accrual.remaining_amount_to_accrue == 0:
            print('no_remaining_amount_to_accrue_skipping_accrual',
                  contract_accrual.remaining_amount_to_accrue)
            return 0.0

        # Calculate accrued amount from remaining amount, not total contract amount
        # This will correctly handle negative amounts (losses/overpayments)
        accrued_amount = contract_accrual.remaining_amount_to_accrue * portion
        print('remaining_amount_to_accrue',
              contract_accrual.remaining_amount_to_accrue)
        print('portion', portion)
        print('accrued_amount', accrued_amount)

        # Calculate sessions being accrued
        sessions_in_month = period.get_sessions_between(
            max(period.start_date, get_month_start(target_month)),
            min(period.end_date, get_month_end(target_month))
        )
        sessions_accrued = min(
            sessions_in_month, contract_accrual.sessions_remaining_to_accrue)

        # Create AccruedPeriod record
        accrued_period = AccruedPeriod(
            contract_accrual_id=contract_accrual.id,
            service_period_id=period.id,
            accrual_date=target_month,
            accrued_amount=accrued_amount,
            accrual_portion=portion,
            status=period.status,
            sessions_in_period=sessions_accrued,
            total_contract_amount=contract.contract_amount,
            status_change_date=period.status_change_date
        )

        self.db.add(accrued_period)

        # Update contract accrual
        contract_accrual.total_amount_accrued += accrued_amount
        contract_accrual.remaining_amount_to_accrue = max(
            0, contract_accrual.total_amount_to_accrue - contract_accrual.total_amount_accrued)
        contract_accrual.total_sessions_accrued += sessions_accrued
        contract_accrual.sessions_remaining_to_accrue = max(
            0, contract_accrual.total_sessions_to_accrue - contract_accrual.total_sessions_accrued)

        # Auto-complete if remaining amount reaches zero or becomes negative
        if contract_accrual.remaining_amount_to_accrue <= 0:
            print('accrual_completed_during_processing_auto_completing',
                  contract_accrual.remaining_amount_to_accrue)
            contract_accrual.accrual_status = ContractAccrualStatus.COMPLETED

            # IMPORTANT: Update contract status when accrual completes
            # This was missing and caused contracts to remain ACTIVE with COMPLETED accruals
            if contract_accrual.total_amount_to_accrue > 0:
                contract.status = ServiceContractStatus.CLOSED
                print('contract_auto_closed_on_accrual_completion', contract.id)
            else:
                contract.status = ServiceContractStatus.CANCELED
                print('contract_auto_canceled_on_accrual_completion', contract.id)

        self.db.commit()

        return accrued_amount

    def _accrue_fully(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date) -> float:
        """Accrue the full remaining amount."""
        remaining_amount = contract_accrual.remaining_amount_to_accrue
        print('accruing_full_remaining_amount', remaining_amount)

        # Create AccruedPeriod record for full remaining amount
        accrued_period = AccruedPeriod(
            contract_accrual_id=contract_accrual.id,
            service_period_id=None,  # No specific period
            accrual_date=target_month,
            accrued_amount=remaining_amount,
            accrual_portion=1.0,  # Full remaining portion
            status=ServicePeriodStatus.ENDED,
            sessions_in_period=contract_accrual.sessions_remaining_to_accrue,
            total_contract_amount=contract.contract_amount
        )

        self.db.add(accrued_period)

        # Update contract accrual to completion
        contract_accrual.total_amount_accrued = contract_accrual.total_amount_to_accrue
        contract_accrual.remaining_amount_to_accrue = 0.0
        contract_accrual.total_sessions_accrued = contract_accrual.total_sessions_to_accrue
        contract_accrual.sessions_remaining_to_accrue = 0

        # Update contract accrual status
        contract_accrual.accrual_status = ContractAccrualStatus.COMPLETED

        # IMPORTANT: Update contract status when full accrual completes
        # Only update if contract is still ACTIVE (avoid overriding explicit status changes)
        if contract.status == ServiceContractStatus.ACTIVE:
            if contract_accrual.total_amount_to_accrue > 0:
                contract.status = ServiceContractStatus.CLOSED
                print('contract_auto_closed_on_full_accrual', contract.id)
            else:
                contract.status = ServiceContractStatus.CANCELED
                print('contract_auto_canceled_on_full_accrual', contract.id)

        self.db.commit()

        return remaining_amount

    def _accrue_remaining(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date) -> float:
        """Accrue the remaining amount for ended contracts."""
        return self._accrue_fully(contract, contract_accrual, target_month)

    def _update_contract_accrual_status(self, contract_accrual: ContractAccrual, status: ContractAccrualStatus):
        """Update ContractAccrual status."""
        contract_accrual.accrual_status = status
        self.db.commit()

    def _update_contract_status(self, contract: ServiceContract, status: ServiceContractStatus):
        """Update ServiceContract status."""
        contract.status = status
        self.db.commit()

    def _add_notification(self, notification_type: str, message: str):
        """Add a notification to the results."""
        self.notifications.append({
            'type': notification_type,
            'message': message,
            'timestamp': date.today().isoformat()
        })

    def adapt_results_for_sync_actions(self, results: Dict, processing_start_time: Optional[float] = None) -> 'SyncActionSummary':
        """
        Adapt contract accrual processing results for sync-actions integration.

        Args:
            results: Raw processing results from process_all_contracts()
            processing_start_time: Optional start time for duration calculation

        Returns:
            SyncActionSummary formatted for sync-actions system
        """
        from datetime import datetime
        from src.api.accruals.schemas import SyncActionSummary

        # Calculate overall status
        overall_status = "SUCCESS"
        if results['failed'] > 0:
            if results['successful'] == 0:
                overall_status = "FAILED"
            else:
                overall_status = "PARTIAL"

        # Calculate financial metrics
        total_amount_accrued = 0.0
        contracts_completed = 0
        contracts_auto_closed = 0
        contracts_auto_canceled = 0
        failed_contract_ids = []

        for result in results['results']:
            if result.status == ProcessingStatus.FAILED:
                failed_contract_ids.append(result.contract_id)

            # Extract accrued amounts from messages (if available)
            if result.message and "Amount:" in result.message:
                try:
                    # Extract amount from messages like "Accrued portion 50.00% - Amount: 1234.56"
                    amount_str = result.message.split("Amount: ")[1].split()[0]
                    total_amount_accrued += float(amount_str)
                except (IndexError, ValueError):
                    pass

            # Count completion events
            if result.message:
                if "completed" in result.message.lower():
                    contracts_completed += 1
                if "closed" in result.message.lower():
                    contracts_auto_closed += 1
                if "canceled" in result.message.lower():
                    contracts_auto_canceled += 1

        # Analyze notifications
        critical_notifications = sum(
            1 for n in results['notifications'] if n.get('type') == 'not_congruent_status')
        warning_notifications = len(
            results['notifications']) - critical_notifications

        # Calculate performance metrics
        processing_duration = None
        contracts_per_second = None
        if processing_start_time:
            processing_duration = datetime.now().timestamp() - processing_start_time
            if processing_duration > 0:
                contracts_per_second = results['total_processed'] / \
                    processing_duration

        # Create breakdown by status
        breakdown_by_status = {
            'SUCCESS': results['successful'],
            'FAILED': results['failed'],
            'SKIPPED': results['skipped']
        }

        # Determine if manual review is required
        manual_review_required = (
            critical_notifications > 0 or
            results['failed'] > 0 or
            # >10% failure rate
            (results['failed'] / max(results['total_processed'], 1)) > 0.1
        )

        return SyncActionSummary(
            action_type="contract_accrual_processing",
            target_period=date.today(),  # This should be passed as parameter
            status=overall_status,
            execution_timestamp=datetime.now().isoformat(),

            # Summary statistics
            total_contracts=results['total_processed'],
            successful_count=results['successful'],
            failed_count=results['failed'],
            skipped_count=results['skipped'],

            # Financial summary
            total_amount_accrued=total_amount_accrued,
            contracts_completed=contracts_completed,
            contracts_auto_closed=contracts_auto_closed,
            contracts_auto_canceled=contracts_auto_canceled,

            # Error and notification summary
            critical_notifications=critical_notifications,
            warning_notifications=warning_notifications,

            # Performance metrics
            processing_duration_seconds=processing_duration,
            contracts_per_second=contracts_per_second,

            # Detailed breakdown
            breakdown_by_status=breakdown_by_status,
            failed_contract_ids=failed_contract_ids,

            # Compliance and audit
            data_consistency_check=results['failed'] == 0,
            manual_review_required=manual_review_required
        )

    def extract_sync_action_details(self, results: Dict) -> List['SyncActionDetail']:
        """
        Extract detailed sync-action information for individual contracts.

        Args:
            results: Raw processing results from process_all_contracts()

        Returns:
            List of SyncActionDetail objects with individual contract information
        """
        from src.api.accruals.schemas import SyncActionDetail

        details = []

        for result in results['results']:
            # Extract accrued amount from message
            accrued_amount = None
            if result.message and "Amount:" in result.message:
                try:
                    amount_str = result.message.split("Amount: ")[1].split()[0]
                    accrued_amount = float(amount_str)
                except (IndexError, ValueError):
                    pass

            # Determine final contract status from message
            final_contract_status = None
            if result.message:
                if "closed" in result.message.lower():
                    final_contract_status = "CLOSED"
                elif "canceled" in result.message.lower():
                    final_contract_status = "CANCELED"
                elif "completed" in result.message.lower():
                    final_contract_status = "COMPLETED"

            # Extract error message for failed cases
            error_message = None
            if result.status == ProcessingStatus.FAILED:
                error_message = result.message

            detail = SyncActionDetail(
                contract_id=result.contract_id,
                processing_status=result.status,
                accrued_amount=accrued_amount,
                final_contract_status=final_contract_status,
                error_message=error_message,
                processing_notes=result.message
            )

            details.append(detail)

        return details

    def _is_period_naturally_completed(self, period: ServicePeriod, target_month: date) -> bool:
        """
        Check if a service period completed naturally (status_change_date after end_date).

        This identifies periods that:
        1. Have status ENDED or DROPPED
        2. Have status_change_date after the service period's end_date
        3. Target month contains the service period's end_date

        Such periods should be fully accrued in the last month of their natural duration.
        """
        if period.status not in [ServicePeriodStatus.ENDED, ServicePeriodStatus.DROPPED]:
            return False

        if not period.status_change_date:
            return False

        # Check if status_change_date is after the service period's end_date
        if period.status_change_date <= period.end_date:
            return False

        # Check if target month contains the service period's end_date
        month_start, month_end = get_month_boundaries(target_month)

        # Target month should contain the service period's end_date
        return month_start <= period.end_date <= month_end

    def _handle_negative_amount_accrual(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date, context: str, service_period_id: Optional[int] = None) -> ContractProcessingResult:
        """
        Handle negative amount accrual with consistent logging and processing.

        Args:
            contract: The service contract
            contract_accrual: The contract accrual object
            target_month: Target month for accrual
            context: Context description for logging and messaging
            service_period_id: Optional service period ID for the result

        Returns:
            ContractProcessingResult with success status
        """
        print(f'negative_amount_accrual_{context}',
              contract_accrual.remaining_amount_to_accrue)
        self._accrue_fully(contract, contract_accrual, target_month)
        self._update_contract_accrual_status(
            contract_accrual, ContractAccrualStatus.COMPLETED)

        # Only update contract status to CANCELED for ACTIVE contracts
        if contract.status == ServiceContractStatus.ACTIVE:
            self._update_contract_status(
                contract, ServiceContractStatus.CANCELED)

        # Generate appropriate message based on context
        if "loss_overpayment" in context:
            message = f"Accrued loss/overpayment for {contract.status.lower()} contract: {contract_accrual.remaining_amount_to_accrue:.2f}"
        else:
            message = f"Negative contract {context} - fully accrued: {contract_accrual.remaining_amount_to_accrue:.2f}"

        return ContractProcessingResult(
            contract_id=contract.id,
            service_period_id=service_period_id,
            status=ProcessingStatus.SUCCESS,
            message=message
        )

    def _handle_zero_amount_completion(self, contract: ServiceContract, contract_accrual: ContractAccrual, context: str) -> ContractProcessingResult:
        """
        Handle zero amount completion with consistent logging and processing.

        Args:
            contract: The service contract
            contract_accrual: The contract accrual object
            context: Context description for logging

        Returns:
            ContractProcessingResult 
        """
        print(f'{context}_remaining_amount_is_zero_auto_completing',
              contract_accrual.remaining_amount_to_accrue)
        self._update_contract_accrual_status(
            contract_accrual, ContractAccrualStatus.COMPLETED)

        # For canceled/closed contracts, return a skip message, for active contracts use completed accrual logic
        if contract.status in [ServiceContractStatus.CANCELED, ServiceContractStatus.CLOSED]:
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SKIPPED,
                message="Contract accrual auto-completed - no remaining amount"
            )
        else:
            return self._handle_completed_accrual(contract, contract_accrual)

    def _handle_zero_amount_contract_resignation(self, contract: ServiceContract, contract_accrual: ContractAccrual, context: str, target_month: Optional[date] = None) -> ContractProcessingResult:
        """
        Handle zero-amount contract resignation with proper status updates and AccruedPeriod creation.

        Args:
            contract: The service contract
            contract_accrual: The contract accrual object
            context: Context description for messaging
            target_month: Optional target month for accrual

        Returns:
            ContractProcessingResult with success status
        """
        print(f'zero_amount_contract_resignation_{context}',
              contract_accrual.remaining_amount_to_accrue)

        # Check if AccruedPeriod already exists (for re-processing completed contracts)
        existing_accrued_periods = contract_accrual.accrued_periods
        if existing_accrued_periods:
            print('zero_amount_contract_already_has_accrued_period_skipping_creation', len(
                existing_accrued_periods))
            return ContractProcessingResult(
                contract_id=contract.id,
                status=ProcessingStatus.SUCCESS,
                message=f"Zero-amount contract {context} - already processed with accrual record"
            )

        # Determine the accrual date - use first day of last credit note month if available, otherwise use target_month
        accrual_date = target_month
        last_credit_note_month_start = self._get_last_credit_note_month_start(
            contract)

        if last_credit_note_month_start:
            accrual_date = last_credit_note_month_start
            print('using_last_credit_note_month_start_for_zero_amount_accrual',
                  last_credit_note_month_start)
        elif target_month:
            accrual_date = target_month
            print('using_target_month_for_zero_amount_accrual', target_month)
        else:
            # Fallback to current month start if no other date available
            from datetime import date
            from src.api.common.utils.datetime import get_month_start
            accrual_date = get_month_start(date.today())
            print('using_current_month_start_for_zero_amount_accrual', accrual_date)

        # Create AccruedPeriod record for audit trail (even though amount is 0)
        accrued_period = AccruedPeriod(
            contract_accrual_id=contract_accrual.id,
            service_period_id=None,  # No specific period for resignations
            accrual_date=accrual_date,
            accrued_amount=0.0,  # Zero amount
            accrual_portion=1.0,  # Full contract "completed"
            status=ServicePeriodStatus.ENDED,  # Resignation is treated as ended
            sessions_in_period=0,  # No sessions for zero-amount contracts
            total_contract_amount=contract.contract_amount  # Should be 0
        )

        self.db.add(accrued_period)

        # Update contract accrual to completion
        contract_accrual.total_amount_accrued = 0.0  # No money accrued
        contract_accrual.remaining_amount_to_accrue = 0.0  # Nothing left to accrue
        contract_accrual.accrual_status = ContractAccrualStatus.COMPLETED

        # Update contract status to CANCELED for resignations
        if contract.status == ServiceContractStatus.ACTIVE:
            contract.status = ServiceContractStatus.CANCELED

        self.db.commit()

        return ContractProcessingResult(
            contract_id=contract.id,
            status=ProcessingStatus.SUCCESS,
            message=f"Zero-amount contract {context} - completed with accrual record on {accrual_date}"
        )

    def _handle_contract_resignation(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date, context: str, is_negative: bool = False) -> ContractProcessingResult:
        """
        Handle contract resignation with consistent processing.

        Args:
            contract: The service contract
            contract_accrual: The contract accrual object
            target_month: Target month for accrual
            context: Context description for messaging
            is_negative: Whether this is a negative amount case

        Returns:
            ContractProcessingResult with success status
        """
        if is_negative:
            print(f'negative_contract_resignation_{context}',
                  contract_accrual.remaining_amount_to_accrue)
            message = f"Negative {context} - fully accrued: {contract_accrual.remaining_amount_to_accrue:.2f}"
        else:
            message = f"{context.capitalize()} - accrued fully"

        self._accrue_fully(contract, contract_accrual, target_month)
        self._update_contract_accrual_status(
            contract_accrual, ContractAccrualStatus.COMPLETED)

        # Only update contract status if it's still ACTIVE
        if contract.status == ServiceContractStatus.ACTIVE:
            self._update_contract_status(
                contract, ServiceContractStatus.CANCELED)

        return ContractProcessingResult(
            contract_id=contract.id,
            status=ProcessingStatus.SUCCESS,
            message=message
        )

    def _handle_educational_status_accrual(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date, educational_status: str) -> ContractProcessingResult:
        """
        Handle accrual for contracts with ended educational status.

        Args:
            contract: The service contract
            contract_accrual: The contract accrual object
            target_month: Target month for accrual
            educational_status: The educational status from Notion

        Returns:
            ContractProcessingResult with success status
        """
        self._accrue_fully(contract, contract_accrual, target_month)
        self._update_contract_accrual_status(
            contract_accrual, ContractAccrualStatus.COMPLETED)

        # Determine contract status based on educational status
        new_status = ServiceContractStatus.CLOSED if is_educational_status_ended(
            educational_status) else ServiceContractStatus.CANCELED
        self._update_contract_status(contract, new_status)

        return ContractProcessingResult(
            contract_id=contract.id,
            status=ProcessingStatus.SUCCESS,
            message=f"Accrued fully and updated to {new_status}"
        )

    def _handle_full_accrual_with_status_update(self, contract: ServiceContract, contract_accrual: ContractAccrual, target_month: date, new_contract_status: ServiceContractStatus, message: str, service_period_id: Optional[int] = None) -> ContractProcessingResult:
        """
        Handle full accrual with contract status update.

        Args:
            contract: The service contract
            contract_accrual: The contract accrual object
            target_month: Target month for accrual
            new_contract_status: New status to set for the contract
            message: Success message for the result
            service_period_id: Optional service period ID for the result

        Returns:
            ContractProcessingResult with success status
        """
        self._accrue_fully(contract, contract_accrual, target_month)
        self._update_contract_accrual_status(
            contract_accrual, ContractAccrualStatus.COMPLETED)
        self._update_contract_status(contract, new_contract_status)

        return ContractProcessingResult(
            contract_id=contract.id,
            service_period_id=service_period_id,
            status=ProcessingStatus.SUCCESS,
            message=message
        )

    def _get_last_credit_note_month_start(self, contract: ServiceContract) -> Optional[date]:
        """
        Find the first day of the month of the last credit note for a contract.

        Args:
            contract: The service contract

        Returns:
            First day of the month of the last credit note, or None if no credit notes found
        """
        if not contract.invoices:
            return None

        # Filter for credit notes (negative amounts and/or invoice numbers starting with 'CN')
        credit_notes = [
            invoice for invoice in contract.invoices
            if (invoice.total_amount < 0 or
                (invoice.invoice_number and invoice.invoice_number.startswith('CN')))
        ]

        if not credit_notes:
            return None

        # Get the latest credit note by invoice_date
        latest_credit_note = max(
            credit_notes, key=lambda inv: inv.invoice_date)
        print('last_credit_note_found', latest_credit_note.invoice_number,
              latest_credit_note.invoice_date)

        # Return the first day of the month of the credit note
        from src.api.common.utils.datetime import get_month_start
        month_start = get_month_start(latest_credit_note.invoice_date)
        print('using_credit_note_month_start_for_accrual', month_start)

        return month_start
