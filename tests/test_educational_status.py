import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.common.constants.services import ServicePeriodStatus, map_educational_status
from src.api.integrations.notion.utils import (
    get_client_educational_data,
    parse_notion_educational_status,
)


class TestMapEducationalStatus:
    def test_maps_known_statuses(self):
        assert map_educational_status("ACTIVE") == ServicePeriodStatus.ACTIVE
        assert map_educational_status("DROPPED") == ServicePeriodStatus.DROPPED
        assert map_educational_status(
            "EARLY_DROPPED") == ServicePeriodStatus.DROPPED
        assert map_educational_status("GRADUATED") == ServicePeriodStatus.ENDED
        assert map_educational_status(
            "POSTPONED") == ServicePeriodStatus.POSTPONED
        assert map_educational_status(
            "SUSPENDED") == ServicePeriodStatus.DROPPED

    def test_unknown_string_defaults_to_active(self):
        assert map_educational_status(
            "SOMETHING_ELSE") == ServicePeriodStatus.ACTIVE

    def test_none_defaults_to_active(self):
        assert map_educational_status(None) == ServicePeriodStatus.ACTIVE

    def test_raw_notion_dict_does_not_raise(self):
        raw = {
            "id": "abc",
            "type": "status",
            "status": {"id": "1", "name": "Dropped", "color": "red"},
        }
        assert map_educational_status(raw) == ServicePeriodStatus.ACTIVE

    def test_empty_string_defaults_to_active(self):
        assert map_educational_status("") == ServicePeriodStatus.ACTIVE


class TestParseNotionEducationalStatus:
    def test_parses_select_property(self):
        prop = {
            "id": "abc",
            "type": "select",
            "select": {"id": "1", "name": "Early Dropped", "color": "red"},
        }
        assert parse_notion_educational_status(prop) == "EARLY_DROPPED"

    def test_parses_status_property(self):
        prop = {
            "id": "abc",
            "type": "status",
            "status": {"id": "1", "name": "Dropped", "color": "red"},
        }
        assert parse_notion_educational_status(prop) == "DROPPED"

    def test_empty_select_returns_none(self):
        prop = {"id": "abc", "type": "select", "select": None}
        assert parse_notion_educational_status(prop) is None

    def test_empty_status_returns_none(self):
        prop = {"id": "abc", "type": "status", "status": None}
        assert parse_notion_educational_status(prop) is None

    def test_none_property_returns_none(self):
        assert parse_notion_educational_status(None) is None

    def test_missing_name_returns_none(self):
        prop = {"type": "status", "status": {"id": "1", "color": "red"}}
        assert parse_notion_educational_status(prop) is None

    def test_never_returns_raw_dict(self):
        prop = {"type": "status", "status": {"name": "Graduated"}}
        result = parse_notion_educational_status(prop)
        assert not isinstance(result, dict)
        assert result == "GRADUATED"


class TestGetClientEducationalData:
    @pytest.mark.asyncio
    async def test_status_type_property_returns_string_not_dict(self):
        client = MagicMock()
        client.get_external_id.return_value = "page-id"
        client.identifier = "user@example.com"
        client.id = 1

        page = {
            "properties": {
                "Educational Status": {
                    "id": "abc",
                    "type": "status",
                    "status": {"id": "1", "name": "Dropped", "color": "red"},
                },
                "Drop Date": {
                    "type": "date",
                    "date": {"start": "2026-09-15"},
                },
            }
        }

        mock_client = AsyncMock()
        mock_client.get_page_content.return_value = page

        with patch(
            "src.api.integrations.notion.config.NotionConfig"
        ), patch(
            "src.api.integrations.notion.client.NotionClient",
            return_value=mock_client,
        ):
            result = await get_client_educational_data(client)

        assert result is not None
        assert result["educational_status"] == "DROPPED"
        assert result["status_change_date"] == date(2026, 9, 15)
        assert not isinstance(result["educational_status"], dict)

    @pytest.mark.asyncio
    async def test_select_type_property_still_works(self):
        client = MagicMock()
        client.get_external_id.return_value = "page-id"
        client.identifier = "user@example.com"
        client.id = 2

        page = {
            "properties": {
                "Educational Status": {
                    "type": "select",
                    "select": {"name": "Graduated"},
                },
                "Certificated At": {
                    "type": "date",
                    "date": {"start": "2026-08-01"},
                },
            }
        }

        mock_client = AsyncMock()
        mock_client.get_page_content.return_value = page

        with patch(
            "src.api.integrations.notion.config.NotionConfig"
        ), patch(
            "src.api.integrations.notion.client.NotionClient",
            return_value=mock_client,
        ):
            result = await get_client_educational_data(client)

        assert result["educational_status"] == "GRADUATED"
        assert result["status_change_date"] == date(2026, 8, 1)
