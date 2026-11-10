import pytest

from src.api.common.constants.service_types import (
    ServiceType,
    SERVICE_TYPE_NAMES,
    SERVICE_KEYWORDS,
    SERVICE_PERIOD_PATTERNS,
    ALL_SERVICE_TYPES,
)
from src.api.services.utils import (
    get_service_type_from_service_name,
    get_service_type_from_service_period_name,
)


class TestAIFlexServiceType:
    def test_ai_flex_enum_value(self):
        assert ServiceType.AI_FLEX == "AI-FLEX"
        assert ServiceType.AI_FLEX.value == "AI-FLEX"

    def test_ai_flex_display_name(self):
        assert SERVICE_TYPE_NAMES[ServiceType.AI_FLEX] == "AI Flex"

    def test_ai_flex_in_all_service_types(self):
        assert ServiceType.AI_FLEX in ALL_SERVICE_TYPES

    @pytest.mark.parametrize(
        "service_name",
        [
            "AI Flex Bootcamp",
            "ai-flex program",
        ],
    )
    def test_classifies_service_name_as_ai_flex(self, service_name):
        assert get_service_type_from_service_name(
            service_name) == ServiceType.AI_FLEX

    @pytest.mark.parametrize(
        "period_name",
        [
            "spain-ai-flex-pt-1",
            "madrid-aiflex-ft-2",
            "cohort-ai-flex",
            "ai-flex-madrid",
        ],
    )
    def test_classifies_service_period_as_ai_flex(self, period_name):
        assert (
            get_service_type_from_service_period_name(period_name)
            == ServiceType.AI_FLEX
        )

    def test_ai_flex_period_beats_data_science_ai_pattern(self):
        """DATA_SCIENCE has '-ai-'; AI_FLEX must win for '-ai-flex-'."""
        assert (
            get_service_type_from_service_period_name("spain-ai-flex-pt-1")
            == ServiceType.AI_FLEX
        )

    def test_bare_flex_does_not_match_ai_flex(self):
        assert get_service_type_from_service_name(
            "Something Flex Cohort") != ServiceType.AI_FLEX
        assert get_service_type_from_service_period_name(
            "spain-flex-pt-3") != ServiceType.AI_FLEX

    def test_ai_flex_keywords_and_patterns_defined(self):
        assert SERVICE_KEYWORDS[ServiceType.AI_FLEX] == ["ai flex", "ai-flex"]
        assert SERVICE_PERIOD_PATTERNS[ServiceType.AI_FLEX] == [
            "-ai-flex-",
            "-aiflex-",
            "-ai-flex",
            "ai-flex-",
        ]
        assert "flex" not in SERVICE_KEYWORDS[ServiceType.AI_FLEX]
        assert "-flex-" not in SERVICE_PERIOD_PATTERNS[ServiceType.AI_FLEX]
