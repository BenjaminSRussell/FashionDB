"""Assert Config.temperature is passed to mlx_lm.generate when supported (#17)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

import fashion_rule_extractor as fre  # noqa: E402


def test_temperature_kwarg_passed_when_accepted():
    fre._TEMP_KWARG_CACHE.clear()
    fre._TEMP_FALLBACK_LOGGED = False
    calls = []

    def fake_generate(model, tokenizer, prompt="", max_tokens=0, verbose=False, **kwargs):
        calls.append(kwargs)
        return '{"has_fashion_rule": false, "rules": []}'

    with patch.object(fre, "generate", fake_generate):
        out = fre._generate_with_temperature(
            MagicMock(), MagicMock(), prompt="hi", max_tokens=16, temperature=0.3,
        )
    assert out.startswith("{")
    assert calls and "temperature" in calls[0]
    assert calls[0]["temperature"] == 0.3


def test_falls_back_when_kwargs_rejected():
    fre._TEMP_KWARG_CACHE.clear()
    fre._TEMP_FALLBACK_LOGGED = False
    calls = []

    def fake_generate(model, tokenizer, prompt="", max_tokens=0, verbose=False, **kwargs):
        if kwargs:
            raise TypeError(f"unexpected keyword: {kwargs}")
        calls.append("bare")
        return "ok"

    with patch.object(fre, "generate", fake_generate):
        out = fre._generate_with_temperature(
            MagicMock(), MagicMock(), prompt="hi", max_tokens=8, temperature=0.3,
        )
    assert out == "ok"
    assert "bare" in calls


if __name__ == "__main__":
    test_temperature_kwarg_passed_when_accepted()
    test_falls_back_when_kwargs_rejected()
    print("ok")
