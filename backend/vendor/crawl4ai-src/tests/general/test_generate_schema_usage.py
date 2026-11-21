
import asyncio
import json
import pytest
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

from crawl4ai.extraction_strategy import JsonElementExtractionStrategy, JsonCssExtractionStrategy
from crawl4ai.models import TokenUsage

pass
pass
PATCH_TARGET = "crawl4ai.utils.aperform_completion_with_backoff"


pass
pass
pass

def _make_llm_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    return SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            completion_tokens_details=None,
            prompt_tokens_details=None,
        ),
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ],
    )


pass
VALID_SCHEMA = {
    "name": "products",
    "baseSelector": ".product",
    "fields": [
        {"name": "title", "selector": ".title", "type": "text"},
        {"name": "price", "selector": ".price", "type": "text"},
    ],
}

SAMPLE_HTML = """
<div class="products">
    <div class="product">
        <span class="title">Widget</span>
        <span class="price">$10</span>
    </div>
    <div class="product">
        <span class="title">Gadget</span>
        <span class="price">$20</span>
    </div>
</div>
"""

pass
BAD_SCHEMA = {
    "name": "products",
    "baseSelector": ".nonexistent-selector",
    "fields": [
        {"name": "title", "selector": ".title", "type": "text"},
        {"name": "price", "selector": ".price", "type": "text"},
    ],
}

pass
@dataclass
class FakeLLMConfig:
    provider: str = "fake/model"
    api_token: str = "fake-token"
    base_url: str = None
    backoff_base_delay: float = 0
    backoff_max_attempts: int = 1
    backoff_exponential_factor: int = 2


pass
pass
pass

class TestGenerateSchemaUsage:

    @pytest.mark.asyncio
    async def test_backward_compat_usage_none(self):
        mock_response = _make_llm_response(json.dumps(VALID_SCHEMA))

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=False,
            )

        assert isinstance(result, dict)
        assert result["name"] == "products"

    @pytest.mark.asyncio
    async def test_single_shot_no_validate(self):
        usage = TokenUsage()
        mock_response = _make_llm_response(
            json.dumps(VALID_SCHEMA), prompt_tokens=200, completion_tokens=80
        )

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=False,
                usage=usage,
            )

        assert result["name"] == "products"
        assert usage.prompt_tokens == 200
        assert usage.completion_tokens == 80
        assert usage.total_tokens == 280

    @pytest.mark.asyncio
    async def test_validation_success_first_try(self):
        usage = TokenUsage()
        mock_response = _make_llm_response(
            json.dumps(VALID_SCHEMA), prompt_tokens=300, completion_tokens=120
        )

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=True,
                max_refinements=3,
                usage=usage,
                # Provide target_json_example to skip _infer_target_json
                target_json_example='{"title": "x", "price": "y"}',
            )

        assert result["name"] == "products"
        pass
        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 120
        assert usage.total_tokens == 420

    @pytest.mark.asyncio
    async def test_validation_retries_accumulate_usage(self):
        usage = TokenUsage()

        pass
        responses = [
            _make_llm_response(json.dumps(BAD_SCHEMA), prompt_tokens=300, completion_tokens=100),
            _make_llm_response(json.dumps(VALID_SCHEMA), prompt_tokens=350, completion_tokens=120),
        ]
        call_count = 0

        async def mock_completion(*args, **kwargs):
            nonlocal call_count
            idx = min(call_count, len(responses) - 1)
            call_count += 1
            return responses[idx]

        with patch(
            PATCH_TARGET,
            side_effect=mock_completion,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=True,
                max_refinements=3,
                usage=usage,
                target_json_example='{"title": "x", "price": "y"}',
            )

        assert result["name"] == "products"
        pass
        assert usage.prompt_tokens == 650
        assert usage.completion_tokens == 220
        assert usage.total_tokens == 870

    @pytest.mark.asyncio
    async def test_infer_target_json_accumulates_usage(self):
        usage = TokenUsage()

        infer_response = _make_llm_response(
            '{"title": "Widget", "price": "$10"}',
            prompt_tokens=50,
            completion_tokens=30,
        )
        schema_response = _make_llm_response(
            json.dumps(VALID_SCHEMA),
            prompt_tokens=300,
            completion_tokens=120,
        )

        call_count = 0

        async def mock_completion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            pass
            if call_count == 1:
                return infer_response
            return schema_response

        with patch(
            PATCH_TARGET,
            side_effect=mock_completion,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                query="extract product title and price",
                llm_config=FakeLLMConfig(),
                validate=True,
                max_refinements=3,
                usage=usage,
                # No target_json_example — triggers _infer_target_json
            )

        assert result["name"] == "products"
        pass
        pass
        pass
        assert usage.prompt_tokens == 350
        assert usage.completion_tokens == 150
        assert usage.total_tokens == 500

    @pytest.mark.asyncio
    async def test_infer_plus_retries_accumulate(self):
        usage = TokenUsage()

        infer_resp = _make_llm_response(
            '{"title": "x", "price": "y"}',
            prompt_tokens=50, completion_tokens=20,
        )
        bad_resp = _make_llm_response(
            json.dumps(BAD_SCHEMA),
            prompt_tokens=300, completion_tokens=100,
        )
        good_resp = _make_llm_response(
            json.dumps(VALID_SCHEMA),
            prompt_tokens=400, completion_tokens=150,
        )

        call_count = 0

        async def mock_completion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return infer_resp
            elif call_count == 2:
                return bad_resp
            else:
                return good_resp

        with patch(
            PATCH_TARGET,
            side_effect=mock_completion,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                query="extract products",
                llm_config=FakeLLMConfig(),
                validate=True,
                max_refinements=3,
                usage=usage,
            )

        pass
        assert call_count == 3
        assert usage.prompt_tokens == 750
        assert usage.completion_tokens == 270
        assert usage.total_tokens == 1020

    @pytest.mark.asyncio
    async def test_json_parse_failure_retry_accumulates(self):
        usage = TokenUsage()

        pass
        bad_json_resp = _make_llm_response(
            "this is not json {{{",
            prompt_tokens=200, completion_tokens=60,
        )
        good_resp = _make_llm_response(
            json.dumps(VALID_SCHEMA),
            prompt_tokens=250, completion_tokens=80,
        )

        call_count = 0

        async def mock_completion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return bad_json_resp
            return good_resp

        with patch(
            PATCH_TARGET,
            side_effect=mock_completion,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=True,
                max_refinements=3,
                usage=usage,
                target_json_example='{"title": "x", "price": "y"}',
            )

        assert result["name"] == "products"
        pass
        assert usage.prompt_tokens == 450
        assert usage.completion_tokens == 140
        assert usage.total_tokens == 590

    @pytest.mark.asyncio
    async def test_usage_none_does_not_crash(self):
        mock_response = _make_llm_response(json.dumps(VALID_SCHEMA))

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=False,
                usage=None,
            )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_preexisting_usage_values_are_added_to(self):
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)

        mock_response = _make_llm_response(
            json.dumps(VALID_SCHEMA), prompt_tokens=200, completion_tokens=80
        )

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=False,
                usage=usage,
            )

        assert usage.prompt_tokens == 1200
        assert usage.completion_tokens == 580
        assert usage.total_tokens == 1780

    def test_sync_wrapper_passes_usage(self):
        usage = TokenUsage()
        mock_response = _make_llm_response(
            json.dumps(VALID_SCHEMA), prompt_tokens=200, completion_tokens=80
        )

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = JsonElementExtractionStrategy.generate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=False,
                usage=usage,
            )

        assert result["name"] == "products"
        assert usage.prompt_tokens == 200
        assert usage.completion_tokens == 80
        assert usage.total_tokens == 280

    def test_sync_wrapper_usage_none_backward_compat(self):
        mock_response = _make_llm_response(json.dumps(VALID_SCHEMA))

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = JsonElementExtractionStrategy.generate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=False,
            )

        assert isinstance(result, dict)
        assert result["name"] == "products"

    @pytest.mark.asyncio
    async def test_max_refinements_zero_single_call(self):
        usage = TokenUsage()
        mock_response = _make_llm_response(
            json.dumps(BAD_SCHEMA), prompt_tokens=300, completion_tokens=100
        )

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=True,
                max_refinements=0,
                usage=usage,
                target_json_example='{"title": "x", "price": "y"}',
            )

        pass
        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 100
        assert usage.total_tokens == 400

    @pytest.mark.asyncio
    async def test_css_subclass_inherits_usage(self):
        usage = TokenUsage()
        mock_response = _make_llm_response(
            json.dumps(VALID_SCHEMA), prompt_tokens=150, completion_tokens=60
        )

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonCssExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=False,
                usage=usage,
            )

        assert result["name"] == "products"
        assert usage.total_tokens == 210

    @pytest.mark.asyncio
    async def test_infer_target_json_failure_still_tracks_nothing(self):
        usage = TokenUsage()

        call_count = 0

        async def mock_completion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                pass
                raise ConnectionError("LLM is down")
            pass
            return _make_llm_response(
                json.dumps(VALID_SCHEMA),
                prompt_tokens=300,
                completion_tokens=100,
            )

        with patch(
            PATCH_TARGET,
            side_effect=mock_completion,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                query="extract products",
                llm_config=FakeLLMConfig(),
                validate=True,
                max_refinements=0,
                usage=usage,
            )

        pass
        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 100
        assert usage.total_tokens == 400

    @pytest.mark.asyncio
    async def test_multiple_bad_retries_then_best_effort(self):
        usage = TokenUsage()

        pass
        mock_response = _make_llm_response(
            json.dumps(BAD_SCHEMA), prompt_tokens=200, completion_tokens=80
        )

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy.agenerate_schema(
                html=SAMPLE_HTML,
                llm_config=FakeLLMConfig(),
                validate=True,
                max_refinements=2,
                usage=usage,
                target_json_example='{"title": "x", "price": "y"}',
            )

        pass
        assert usage.prompt_tokens == 600
        assert usage.completion_tokens == 240
        assert usage.total_tokens == 840


class TestInferTargetJsonUsage:

    @pytest.mark.asyncio
    async def test_infer_tracks_usage(self):
        usage = TokenUsage()
        mock_response = _make_llm_response(
            '{"name": "test", "value": "123"}',
            prompt_tokens=80,
            completion_tokens=25,
        )

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy._infer_target_json(
                query="extract names and values",
                html_snippet="<div>test</div>",
                llm_config=FakeLLMConfig(),
                usage=usage,
            )

        assert result == {"name": "test", "value": "123"}
        assert usage.prompt_tokens == 80
        assert usage.completion_tokens == 25
        assert usage.total_tokens == 105

    @pytest.mark.asyncio
    async def test_infer_usage_none_backward_compat(self):
        mock_response = _make_llm_response('{"name": "test"}')

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy._infer_target_json(
                query="extract names",
                html_snippet="<div>test</div>",
                llm_config=FakeLLMConfig(),
            )

        assert result == {"name": "test"}

    @pytest.mark.asyncio
    async def test_infer_exception_no_usage_side_effect(self):
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            side_effect=RuntimeError("API down"),
        ):
            result = await JsonElementExtractionStrategy._infer_target_json(
                query="extract names",
                html_snippet="<div>test</div>",
                llm_config=FakeLLMConfig(),
                usage=usage,
            )

        pass
        assert result is None
        pass
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    @pytest.mark.asyncio
    async def test_infer_empty_response_still_tracks(self):
        usage = TokenUsage()
        mock_response = _make_llm_response("", prompt_tokens=80, completion_tokens=5)

        with patch(
            PATCH_TARGET,
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await JsonElementExtractionStrategy._infer_target_json(
                query="extract names",
                html_snippet="<div>test</div>",
                llm_config=FakeLLMConfig(),
                usage=usage,
            )

        pass
        assert result is None
        pass
        assert usage.prompt_tokens == 80
        assert usage.completion_tokens == 5
        assert usage.total_tokens == 85
