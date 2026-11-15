"""Billing / usage-history coordinator for SJ Water Hub."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SJWaterHubApiClient
from .const import DOMAIN
from .parsing import parse_bills, parse_usage, summarize

_LOGGER = logging.getLogger(__name__)

# Bills arrive about every two months; polling a few times a day is plenty.
BILLING_SCAN_INTERVAL = timedelta(hours=6)


class SJWaterHubBillingCoordinator(DataUpdateCoordinator):
    """Fetch the bill and meter-read spreadsheets."""

    def __init__(self, hass: HomeAssistant, entry, client: SJWaterHubApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_billing",
            update_interval=BILLING_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            bills_text, usage_text = await self.client.async_get_billing_data()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"SJ Water billing download failed: {err}") from err

        bills = parse_bills(bills_text)
        reads = parse_usage(usage_text)
        if not bills and not reads:
            raise UpdateFailed("SJ Water spreadsheets contained no rows")
        data = summarize(bills, reads)
        _LOGGER.debug("SJ Water billing summary: %s", data)
        return data
