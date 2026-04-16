from unittest.mock import MagicMock, patch

from anthropic.types import TextBlock

from app.services.ai_analyzer import analyze_symptoms_with_ai


def _make_args(**overrides):
    base = {
        "symptoms": ["headache", "fever"],
        "duration_days": 2,
        "severity": "moderate",
        "age": 35,
        "additional_info": "",
        "rule_based_results": {
            "urgency": "routine",
            "recommended_action": "See primary care",
            "possible_conditions": [
                {"condition": "Viral infection", "probability": "high", "category": "infectious"},
            ],
        },
    }
    base.update(overrides)
    return base


def _mock_client_returning(content_blocks):
    message = MagicMock()
    message.content = content_blocks
    client = MagicMock()
    client.messages.create.return_value = message
    return client


class TestAnalyzeSymptoms:
    def test_returns_text_from_first_text_block(self):
        text_block = TextBlock(type="text", text="Clinical summary here.", citations=None)
        with patch("app.services.ai_analyzer.anthropic.Anthropic", return_value=_mock_client_returning([text_block])):
            result = analyze_symptoms_with_ai(**_make_args())
        assert result == "Clinical summary here."

    def test_skips_non_text_blocks_and_returns_first_text(self):
        non_text = MagicMock(spec=[])
        text_block = TextBlock(type="text", text="Actual analysis.", citations=None)
        with patch("app.services.ai_analyzer.anthropic.Anthropic", return_value=_mock_client_returning([non_text, text_block])):
            result = analyze_symptoms_with_ai(**_make_args())
        assert result == "Actual analysis."

    def test_no_text_block_returns_unavailable(self):
        non_text = MagicMock(spec=[])
        with patch("app.services.ai_analyzer.anthropic.Anthropic", return_value=_mock_client_returning([non_text])):
            result = analyze_symptoms_with_ai(**_make_args())
        assert result == "AI analysis unavailable."

    def test_empty_content_returns_unavailable(self):
        with patch("app.services.ai_analyzer.anthropic.Anthropic", return_value=_mock_client_returning([])):
            result = analyze_symptoms_with_ai(**_make_args())
        assert result == "AI analysis unavailable."

    def test_api_exception_returns_unavailable(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("API down")
        with patch("app.services.ai_analyzer.anthropic.Anthropic", return_value=client):
            result = analyze_symptoms_with_ai(**_make_args())
        assert result == "AI analysis unavailable."

    def test_handles_no_conditions(self):
        text_block = TextBlock(type="text", text="OK.", citations=None)
        with patch("app.services.ai_analyzer.anthropic.Anthropic", return_value=_mock_client_returning([text_block])) as mocked:
            analyze_symptoms_with_ai(**_make_args(rule_based_results={"possible_conditions": []}))
        user_msg = mocked.return_value.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "None matched" in user_msg

    def test_uses_model_from_settings(self):
        text_block = TextBlock(type="text", text="OK.", citations=None)
        with patch("app.services.ai_analyzer.anthropic.Anthropic", return_value=_mock_client_returning([text_block])) as mocked:
            analyze_symptoms_with_ai(**_make_args())
        call_kwargs = mocked.return_value.messages.create.call_args.kwargs
        assert call_kwargs["model"].startswith("claude-")
