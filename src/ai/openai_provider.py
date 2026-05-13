import ssl
from typing import Callable

import httpx
from openai import OpenAI

from shared import ctx
from src.runtime.settings import Config, load_current_settings

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1/"


def is_default_openai_endpoint(endpoint: str | None) -> bool:
    return not endpoint or "api.openai.com" in endpoint


def resolve_openai_base_url(endpoint: str | None) -> str:
    if is_default_openai_endpoint(endpoint):
        return DEFAULT_OPENAI_BASE_URL
    return f"{str(endpoint).rstrip('/')}/openai/v1/"


class OpenAIClientProvider:
    def __init__(
        self,
        provider_config: Config,
        ssl_context: ssl.SSLContext | None = None,
        http_client_factory: Callable[..., httpx.Client] | None = None,
    ):
        self._config = provider_config
        self._ssl_context = ssl_context or ctx
        self._http_client_factory = http_client_factory or httpx.Client
        self._http_client: httpx.Client | None = None
        self._client: OpenAI | None = None

    def _build_auth_headers(self) -> dict[str, str]:
        if is_default_openai_endpoint(self._config.openai_endpoint):
            return {"Authorization": f"Bearer {self._config.openai_api_key}"}
        return {"api-key": self._config.openai_api_key}

    def _auth_request_hook(self, request: httpx.Request) -> None:
        auth_headers = self._build_auth_headers()
        for key, value in auth_headers.items():
            if key not in request.headers:
                request.headers[key] = value

    @property
    def http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = self._http_client_factory(
                verify=self._ssl_context,
                event_hooks={"request": [self._auth_request_hook]},
            )
        return self._http_client

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            organization = self._config.openai_org_id or None
            self._client = OpenAI(
                http_client=self.http_client,
                base_url=resolve_openai_base_url(self._config.openai_endpoint),
                api_key=self._config.openai_api_key,
                organization=organization,
            )
        return self._client

    def close(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None
        self._client = None


def get_openai_client(provider_config: Config | None = None) -> OpenAI:
    provider = OpenAIClientProvider(provider_config or load_current_settings())
    return provider.client
