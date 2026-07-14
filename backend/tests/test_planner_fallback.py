import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock


def _good_steps():
    return [
        {"step_id": "step_1", "name": "Navigate to Google", "agent_type": "browser", "action": "navigate", "parameters": {"url": "https://google.com"}},
        {"step_id": "step_2", "name": "Take screenshot", "agent_type": "computer", "action": "screenshot", "parameters": {}},
    ]


def _bad_steps():
    return [{"step_id": "step_1", "name": "do", "agent_type": "invalid", "action": "do_something"}]


def _make_service(mock_app):
    from app.services.planner import PlannerService
    with patch.object(PlannerService, '__init__', lambda self: setattr(self, 'app', mock_app)):
        return PlannerService()


def _settings_dict(**overrides):
    defaults = {
        "LOCAL_PLANNER_RETRY_COUNT": 1,
        "WORKFLOW_MIN_QUALITY_SCORE": 70,
        "CLOUD_FALLBACK_ENABLED": False,
        "CLOUD_AI_PROVIDER": "openai",
        "CLOUD_AI_MODEL": "gpt-4o-mini",
        "CLOUD_AI_API_KEY": "",
        "CLOUD_FALLBACK_MAX_ATTEMPTS": 1,
        "CLOUD_FALLBACK_DAILY_LIMIT": 20,
        "CREDENTIAL_ENCRYPTION_KEY": "",
    }
    defaults.update(overrides)
    return defaults


class TestPlannerRetry:
    @pytest.mark.asyncio
    async def test_single_retry_on_low_quality(self):
        call_count_ref = [0]

        async def mock_ainvoke(state):
            call_count_ref[0] += 1
            if call_count_ref[0] == 1:
                return {"steps": _bad_steps(), "parsed_intent": "browser_search", "errors": []}
            return {"steps": _good_steps(), "parsed_intent": "browser_search", "errors": []}

        mock_app = MagicMock()
        mock_app.ainvoke = mock_ainvoke

        val_call_count = [0]

        def mock_validate(self_inner, workflow, prompt):
            val_call_count[0] += 1
            steps = workflow.get("steps", [])
            if val_call_count[0] == 1:
                return {"is_valid": False, "score": 30, "errors": [{"code": "test", "message": "bad"}]}
            return {"is_valid": True, "score": 85, "errors": []}

        with patch("app.services.workflow_validator.WorkflowValidator.validate", mock_validate):
            service = _make_service(mock_app)
            result = await service.generate_workflow_steps("search google for test")
            assert result["planner_metadata"]["local_attempts"] >= 2
            assert result["planner_metadata"]["quality_score"] == 85

    @pytest.mark.asyncio
    async def test_no_retry_when_quality_good(self):
        mock_app = MagicMock()

        async def mock_ainvoke(state):
            return {"steps": _good_steps(), "parsed_intent": "browser_search", "errors": []}

        mock_app.ainvoke = mock_ainvoke

        def mock_validate(self_inner, workflow, prompt):
            return {"is_valid": True, "score": 90, "errors": []}

        with patch("app.services.workflow_validator.WorkflowValidator.validate", mock_validate):
            service = _make_service(mock_app)
            result = await service.generate_workflow_steps("search google")
            assert result["planner_metadata"]["local_attempts"] == 1


class TestCloudFallback:
    @pytest.mark.asyncio
    async def test_cloud_fallback_triggered_on_low_quality(self):
        mock_app = MagicMock()

        async def mock_ainvoke(state):
            return {"steps": _bad_steps(), "parsed_intent": "browser_search", "errors": []}

        mock_app.ainvoke = mock_ainvoke

        def mock_validate(self_inner, workflow, prompt):
            steps = workflow.get("steps", [])
            if steps and steps[0].get("agent_type") in ("browser", "computer"):
                return {"is_valid": True, "score": 90, "errors": []}
            return {"is_valid": False, "score": 30, "errors": []}

        mock_cloud_result = MagicMock(
            success=True, workflow={"steps": _good_steps()},
            tokens_input=100, tokens_output=200, latency_ms=1500.0, error=None
        )

        with patch("app.services.workflow_validator.WorkflowValidator.validate", mock_validate), \
             patch("app.services.credential_store.get_api_key", new_callable=AsyncMock, return_value="sk-test-key"), \
             patch("app.services.cloud_planner.generate_cloud_workflow", new_callable=AsyncMock, return_value=mock_cloud_result), \
             patch("app.services.fallback_tracker.get_daily_usage_count", new_callable=AsyncMock, return_value=5), \
             patch("app.services.fallback_tracker.record_fallback_usage", new_callable=AsyncMock):
            service = _make_service(mock_app)
            with patch("app.core.config.settings") as mock_settings:
                for k, v in _settings_dict(CLOUD_FALLBACK_ENABLED=True, CLOUD_AI_API_KEY="").items():
                    setattr(mock_settings, k, v)
                result = await service.generate_workflow_steps("search google", user_id="user123")
                assert result["planner_metadata"]["planner_source"] == "cloud_fallback"
                assert result["planner_metadata"]["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_cloud_fallback_disabled_no_cloud_call(self):
        mock_app = MagicMock()

        async def mock_ainvoke(state):
            return {"steps": _bad_steps(), "parsed_intent": "browser_search", "errors": []}

        mock_app.ainvoke = mock_ainvoke

        def mock_validate(self_inner, workflow, prompt):
            return {"is_valid": False, "score": 20, "errors": []}

        with patch("app.services.workflow_validator.WorkflowValidator.validate", mock_validate):
            service = _make_service(mock_app)
            with patch("app.core.config.settings") as mock_settings:
                for k, v in _settings_dict(CLOUD_FALLBACK_ENABLED=False).items():
                    setattr(mock_settings, k, v)
                result = await service.generate_workflow_steps("test prompt")
                assert result["planner_metadata"]["planner_source"] == "ollama"
                assert result["planner_metadata"]["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_cloud_fallback_daily_limit_reached(self):
        mock_app = MagicMock()

        async def mock_ainvoke(state):
            return {"steps": _bad_steps(), "parsed_intent": "browser_search", "errors": []}

        mock_app.ainvoke = mock_ainvoke

        def mock_validate(self_inner, workflow, prompt):
            return {"is_valid": False, "score": 20, "errors": []}

        with patch("app.services.workflow_validator.WorkflowValidator.validate", mock_validate), \
             patch("app.services.fallback_tracker.get_daily_usage_count", new_callable=AsyncMock, return_value=20), \
             patch("app.services.cloud_planner.generate_cloud_workflow", new_callable=AsyncMock) as mock_cloud:
            service = _make_service(mock_app)
            with patch("app.core.config.settings") as mock_settings:
                for k, v in _settings_dict(CLOUD_FALLBACK_ENABLED=True, CLOUD_AI_API_KEY="sk-key").items():
                    setattr(mock_settings, k, v)
                result = await service.generate_workflow_steps("test", user_id="user123")
                mock_cloud.assert_not_called()

    @pytest.mark.asyncio
    async def test_cloud_api_failure_records_usage(self):
        mock_app = MagicMock()

        async def mock_ainvoke(state):
            return {"steps": _bad_steps(), "parsed_intent": "browser_search", "errors": []}

        mock_app.ainvoke = mock_ainvoke

        def mock_validate(self_inner, workflow, prompt):
            return {"is_valid": False, "score": 20, "errors": []}

        mock_cloud_result = MagicMock(
            success=False, error="API key invalid",
            tokens_input=0, tokens_output=0, latency_ms=500.0, workflow=None
        )

        with patch("app.services.workflow_validator.WorkflowValidator.validate", mock_validate), \
             patch("app.services.credential_store.get_api_key", new_callable=AsyncMock, return_value="sk-test-key"), \
             patch("app.services.cloud_planner.generate_cloud_workflow", new_callable=AsyncMock, return_value=mock_cloud_result), \
             patch("app.services.fallback_tracker.get_daily_usage_count", new_callable=AsyncMock, return_value=0), \
             patch("app.services.fallback_tracker.record_fallback_usage", new_callable=AsyncMock) as mock_record:
            service = _make_service(mock_app)
            with patch("app.core.config.settings") as mock_settings:
                for k, v in _settings_dict(CLOUD_FALLBACK_ENABLED=True, CLOUD_AI_API_KEY="").items():
                    setattr(mock_settings, k, v)
                result = await service.generate_workflow_steps("test", user_id="user123")
                mock_record.assert_called_once()
                assert mock_record.call_args[1]["success"] is False


class TestPlannerMetadata:
    @pytest.mark.asyncio
    async def test_metadata_present_in_success(self):
        mock_app = MagicMock()

        async def mock_ainvoke(state):
            return {"steps": _good_steps(), "parsed_intent": "browser_search", "errors": []}

        mock_app.ainvoke = mock_ainvoke

        def mock_validate(self_inner, workflow, prompt):
            return {"is_valid": True, "score": 90, "errors": []}

        with patch("app.services.workflow_validator.WorkflowValidator.validate", mock_validate):
            service = _make_service(mock_app)
            result = await service.generate_workflow_steps("search google")
            assert "planner_metadata" in result
            assert "planner_source" in result["planner_metadata"]
            assert "quality_score" in result["planner_metadata"]
            assert "local_attempts" in result["planner_metadata"]

    @pytest.mark.asyncio
    async def test_rule_based_fallback_metadata(self):
        mock_app = MagicMock()

        async def mock_ainvoke(state):
            return {"steps": [], "parsed_intent": "general_automation", "errors": []}

        mock_app.ainvoke = mock_ainvoke

        service = _make_service(mock_app)
        with patch("app.core.config.settings") as mock_settings:
            for k, v in _settings_dict().items():
                setattr(mock_settings, k, v)
            with patch.object(service, "_generate_rule_based_fallback", new_callable=AsyncMock) as mock_rule:
                mock_rule.return_value = {"steps": _good_steps()}
                result = await service.generate_workflow_steps("search google")
                assert result["planner_metadata"]["planner_source"] == "rule_based"
