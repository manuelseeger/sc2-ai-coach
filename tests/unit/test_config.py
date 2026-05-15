from src.ai.pricing import ModelPricingOverride
from src.runtime.settings import AudioMode, Config


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


def test_microphone_autoselection_skips_text_mode(monkeypatch):
    calls: list[str] = []

    def fake_select_preferred_microphone_index():
        calls.append("selected")
        return 9

    monkeypatch.setattr(
        "src.runtime.settings.select_preferred_microphone_index",
        fake_select_preferred_microphone_index,
    )

    config = Config.model_construct(
        audiomode=AudioMode.text,
        microphone_index=None,
    )

    config._resolve_microphone_index()

    assert config.microphone_index is None
    assert calls == []


def test_microphone_autoselection_runs_for_full_mode(monkeypatch):
    monkeypatch.setattr(
        "src.runtime.settings.select_preferred_microphone_index",
        lambda: 9,
    )

    config = Config.model_construct(
        audiomode=AudioMode.full,
        microphone_index=None,
    )

    config._resolve_microphone_index()

    assert config.microphone_index == 9
