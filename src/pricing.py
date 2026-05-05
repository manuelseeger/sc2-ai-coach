from __future__ import annotations

from pydantic import BaseModel


def normalize_model_name(model_name: str | None) -> str | None:
    if model_name is None:
        return None
    normalized = model_name.strip().lower()
    return normalized or None


class ModelPricing(BaseModel):
    prompt_per_million: float
    cached_prompt_per_million: float = 0
    completion_per_million: float

    @property
    def prompt(self) -> float:
        return self.prompt_per_million / 1_000_000

    @property
    def cached_prompt(self) -> float:
        return self.cached_prompt_per_million / 1_000_000

    @property
    def completion(self) -> float:
        return self.completion_per_million / 1_000_000


class ModelPricingOverride(BaseModel):
    prompt_per_million: float | None = None
    cached_prompt_per_million: float | None = None
    completion_per_million: float | None = None


MODEL_PRICING_PER_MILLION: dict[str, ModelPricing] = {
    "gpt-5.5": ModelPricing(
        prompt_per_million=5.0,
        cached_prompt_per_million=0.5,
        completion_per_million=30.0,
    ),
    "gpt-5.5-pro": ModelPricing(
        prompt_per_million=30.0,
        cached_prompt_per_million=0,
        completion_per_million=180.0,
    ),
    "gpt-5.4": ModelPricing(
        prompt_per_million=2.5,
        cached_prompt_per_million=0.25,
        completion_per_million=15.0,
    ),
    "gpt-5.4-mini": ModelPricing(
        prompt_per_million=0.75,
        cached_prompt_per_million=0.075,
        completion_per_million=4.5,
    ),
    "gpt-5.4-nano": ModelPricing(
        prompt_per_million=0.2,
        cached_prompt_per_million=0.02,
        completion_per_million=1.25,
    ),
    "gpt-5.4-pro": ModelPricing(
        prompt_per_million=30.0,
        cached_prompt_per_million=0,
        completion_per_million=180.0,
    ),
    "gpt-5.3-chat-latest": ModelPricing(
        prompt_per_million=1.75,
        cached_prompt_per_million=0.175,
        completion_per_million=14.0,
    ),
    "gpt-5.3-codex": ModelPricing(
        prompt_per_million=1.75,
        cached_prompt_per_million=0.175,
        completion_per_million=14.0,
    ),
    "gpt-realtime-1.5": ModelPricing(
        prompt_per_million=4.0,
        cached_prompt_per_million=0.4,
        completion_per_million=16.0,
    ),
    "gpt-realtime-mini": ModelPricing(
        prompt_per_million=0.6,
        cached_prompt_per_million=0.06,
        completion_per_million=2.4,
    ),
}


def get_default_model_pricing(model_name: str | None) -> ModelPricing | None:
    normalized = normalize_model_name(model_name)
    if normalized is None:
        return None
    pricing = MODEL_PRICING_PER_MILLION.get(normalized)
    if pricing is None:
        return None
    return pricing.model_copy(deep=True)