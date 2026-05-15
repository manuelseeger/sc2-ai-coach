from src.ai.pricing import ModelPricingOverride
from src.runtime.settings import Config


def test_model_pricing_defaults_to_builtin_lookup():
    config = Config.model_construct(
        gpt_model="gpt-5.4",
        gpt_prompt_pricing_per_million=None,
        gpt_cached_prompt_pricing_per_million=None,
        gpt_completion_pricing_per_million=None,
        model_pricing_per_million={},
    )

    pricing = config.get_model_pricing()

    assert pricing.prompt_per_million == 2.5
    assert pricing.cached_prompt_per_million == 0.25
    assert pricing.completion_per_million == 15.0


def test_model_pricing_config_overrides_builtin_lookup():
    config = Config.model_construct(
        gpt_model="gpt-5.4",
        gpt_prompt_pricing_per_million=3.5,
        gpt_cached_prompt_pricing_per_million=0.35,
        gpt_completion_pricing_per_million=18.0,
        model_pricing_per_million={
            "gpt-5.4": ModelPricingOverride(
                prompt_per_million=3.0,
                cached_prompt_per_million=0.3,
                completion_per_million=17.0,
            )
        },
    )

    pricing = config.get_model_pricing()

    assert pricing.prompt_per_million == 3.5
    assert pricing.cached_prompt_per_million == 0.35
    assert pricing.completion_per_million == 18.0


def test_unknown_model_pricing_falls_back_to_configured_model():
    config = Config.model_construct(
        gpt_model="gpt-5.4",
        gpt_prompt_pricing_per_million=None,
        gpt_cached_prompt_pricing_per_million=None,
        gpt_completion_pricing_per_million=None,
        model_pricing_per_million={},
    )

    pricing = config.get_model_pricing("custom-deployment-name")

    assert pricing.prompt_per_million == 2.5
    assert pricing.cached_prompt_per_million == 0.25
    assert pricing.completion_per_million == 15.0
