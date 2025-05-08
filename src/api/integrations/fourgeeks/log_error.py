from fastapi.logger import logger

def log_enrollment_error(error: Exception, cohort_slug: str, contract_id: int) -> str:
    error_msg = f"Error processing enrollment for {cohort_slug} in contract {contract_id}: {str(error)}"
    logger.error(error_msg)
    return error_msg


def log_contract_error(error: Exception, contract_id: int) -> str:
    error_msg = f"Error processing contract {contract_id}: {str(error)}"
    logger.error(error_msg)
    return error_msg


def log_student_error(error: Exception) -> str:
    error_msg = f"Error processing student: {str(error)}"
    logger.error(error_msg)
    return error_msg
