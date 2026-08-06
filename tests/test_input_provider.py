from __future__ import annotations

import pytest

from respeaker_led.core.effect_schema import InputContext
from respeaker_led.engine.input_provider import PolledInputProvider


def _context(now: float) -> InputContext:
    return InputContext(
        now=now,
        led_count=12,
        config={},
        previous_inputs={},
    )


def test_polled_input_provider_caches_one_snapshot_until_next_interval():
    reads: list[int] = []

    def reader():
        reads.append(len(reads) + 1)
        return {"value": reads[-1]}

    provider = PolledInputProvider("demo", reader, max_hz=10.0)

    assert provider.refresh(1.0) is True
    assert provider.sample(_context(1.0)) == {"value": 1}
    assert provider.refresh(1.05) is False
    assert provider.sample(_context(1.05)) == {"value": 1}
    assert provider.refresh(1.1) is True
    assert provider.sample(_context(1.1)) == {"value": 2}
    assert reads == [1, 2]


def test_polled_input_provider_exposes_failure_until_a_poll_recovers():
    responses = iter((RuntimeError("device busy"), {"value": 2}))

    def reader():
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    provider = PolledInputProvider("demo", reader, max_hz=10.0)

    assert provider.refresh(1.0) is True
    with pytest.raises(RuntimeError, match="device busy"):
        provider.sample(_context(1.0))
    assert provider.status(1.0)["available"] is False

    assert provider.refresh(1.1) is True
    assert provider.sample(_context(1.1)) == {"value": 2}
    assert provider.status(1.1)["available"] is True
