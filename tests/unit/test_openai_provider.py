from types import SimpleNamespace
from unittest.mock import MagicMock, sentinel

import httpx

from src.ai.aicoach import AICoach
from src.ai.openai_provider import (
    DEFAULT_OPENAI_BASE_URL,
    OpenAIClientProvider,
    resolve_openai_base_url,
)
from tests.critic import LmmCritic


def make_provider_config(endpoint=None, api_key="test-key", org_id="test-org"):
    return SimpleNamespace(
        openai_endpoint=endpoint,
        openai_api_key=api_key,
        openai_org_id=org_id,
    )


def test_resolve_openai_base_url_defaults_to_openai():
    assert resolve_openai_base_url(None) == DEFAULT_OPENAI_BASE_URL
    assert resolve_openai_base_url("") == DEFAULT_OPENAI_BASE_URL
    assert resolve_openai_base_url("https://api.openai.com") == DEFAULT_OPENAI_BASE_URL


def test_resolve_openai_base_url_normalizes_custom_endpoint():
    assert (
        resolve_openai_base_url("https://example.openai.azure.com/")
        == "https://example.openai.azure.com/openai/v1/"
    )


def test_provider_uses_ssl_context_and_bearer_header_for_default_openai(mocker):
    openai_ctor = mocker.patch("src.ai.openai_provider.OpenAI", autospec=True)
    http_client_factory = mocker.Mock()
    http_client = mocker.Mock()
    http_client_factory.return_value = http_client
    provider = OpenAIClientProvider(
        provider_config=make_provider_config(endpoint=None),
        ssl_context=sentinel.ssl_context,
        http_client_factory=http_client_factory,
    )

    provider.client

    http_client_factory.assert_called_once()
    http_client_kwargs = http_client_factory.call_args.kwargs
    assert http_client_kwargs["verify"] is sentinel.ssl_context

    hook = http_client_kwargs["event_hooks"]["request"][0]
    request = httpx.Request("GET", DEFAULT_OPENAI_BASE_URL)
    hook(request)
    assert request.headers["Authorization"] == "Bearer test-key"

    openai_ctor.assert_called_once_with(
        http_client=http_client,
        base_url=DEFAULT_OPENAI_BASE_URL,
        api_key="test-key",
        organization="test-org",
    )


def test_provider_adds_api_key_header_for_custom_endpoint(mocker):
    openai_ctor = mocker.patch("src.ai.openai_provider.OpenAI", autospec=True)
    http_client_factory = mocker.Mock()
    http_client = mocker.Mock()
    http_client_factory.return_value = http_client
    provider = OpenAIClientProvider(
        provider_config=make_provider_config(
            endpoint="https://example.openai.azure.com/", api_key="azure-key"
        ),
        ssl_context=sentinel.ssl_context,
        http_client_factory=http_client_factory,
    )

    provider.client

    hook = http_client_factory.call_args.kwargs["event_hooks"]["request"][0]
    request = httpx.Request(
        "GET",
        "https://example.openai.azure.com/openai/v1/responses",
        headers={"Authorization": "Bearer sdk-key"},
    )
    hook(request)
    assert request.headers["Authorization"] == "Bearer sdk-key"
    assert request.headers["api-key"] == "azure-key"

    openai_ctor.assert_called_once_with(
        http_client=http_client,
        base_url="https://example.openai.azure.com/openai/v1/",
        api_key="azure-key",
        organization="test-org",
    )


def test_aicoach_uses_injected_client():
    client = MagicMock()

    coach = AICoach(client=client)

    assert coach.client is client


def test_lmmcritic_uses_provider_by_default(mocker):
    client = MagicMock()
    provider = mocker.patch("tests.critic.get_openai_client", return_value=client)

    critic = LmmCritic()

    assert critic.client is client
    provider.assert_called_once_with()


def test_lmmcritic_uses_injected_client(mocker):
    client = MagicMock()
    provider = mocker.patch("tests.critic.get_openai_client")

    critic = LmmCritic(client=client)

    assert critic.client is client
    provider.assert_not_called()


def test_lmmcritic_uses_responses_structured_output():
    client = MagicMock()
    client.responses.create.return_value = SimpleNamespace(
        output_text='{"passed": true, "justification": "looks good"}'
    )
    critic = LmmCritic(client=client)
    critic.init("Judge the answer strictly.")

    result = critic.evaluate("QUESTION: hi", "ANSWER: hello")

    assert result.passed is True
    request = client.responses.create.call_args.kwargs
    assert request["instructions"] == "Judge the answer strictly."
    assert request["store"] is False
    assert request["text"]["format"]["type"] == "json_schema"
    assert "Response under evaluation" in request["input"][0]["content"]
