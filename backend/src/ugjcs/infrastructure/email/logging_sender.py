"""Stands in for a real mail transport. See Plan 3 Task 7's scope decision: SES sandbox
mode cannot reach an unverified assessor inbox, so verification links are logged instead.
"""

import logging

logger = logging.getLogger(__name__)


class LoggingEmailSender:
    async def send_verification(self, to: str, link: str) -> None:
        logger.info("verification link for %s: %s", to, link)
