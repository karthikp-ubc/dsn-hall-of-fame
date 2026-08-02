"""Regression tests for dblp._get_with_retries — the shared retry/backoff
helper behind search_pub, search, and get_affiliation.

Existing per-function tests (test_bug1_search_pub_retry.py, etc.) cover the
"succeeds immediately" and "fails 5x and gives up" ends of this helper, but
not the actual reason it retries with a growing delay instead of firing
right back: a 429 means dblp is asking us to slow down. These tests pin
that middle path directly against _get_with_retries so a future change to
the backoff logic can't silently break it while the surrounding callers'
tests keep passing.
"""
import dblp

from helpers import FakeResponse


def test_returns_response_immediately_on_200(monkeypatch):
    ok_response = FakeResponse(json_data={"ok": True})
    calls = {"n": 0}

    def get(*args, **kwargs):
        calls["n"] += 1
        return ok_response

    monkeypatch.setattr(dblp.requests, "get", get)

    result = dblp._get_with_retries("http://example.test", {}, "ctx")

    assert result is ok_response
    assert calls["n"] == 1


def test_retries_after_429_then_succeeds_with_backoff(monkeypatch):
    ok_response = FakeResponse(json_data={"ok": True})
    calls = {"n": 0}

    def get(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(status_code=429)
        return ok_response

    sleeps = []
    monkeypatch.setattr(dblp.requests, "get", get)
    monkeypatch.setattr(dblp.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = dblp._get_with_retries("http://example.test", {}, "ctx")

    assert result is ok_response
    assert calls["n"] == 2
    assert sleeps == [5], "first backoff after a 429 should be the base 5s delay"


def test_backoff_doubles_across_repeated_429s(monkeypatch):
    ok_response = FakeResponse(json_data={"ok": True})
    calls = {"n": 0}

    def get(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] <= 3:
            return FakeResponse(status_code=429)
        return ok_response

    sleeps = []
    monkeypatch.setattr(dblp.requests, "get", get)
    monkeypatch.setattr(dblp.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = dblp._get_with_retries("http://example.test", {}, "ctx")

    assert result is ok_response
    assert sleeps == [5, 10, 20], "backoff should double after each successive 429"


def test_gives_up_after_5_attempts_of_persistent_5xx(monkeypatch):
    calls = {"n": 0}

    def get(*args, **kwargs):
        calls["n"] += 1
        return FakeResponse(status_code=503)

    monkeypatch.setattr(dblp.requests, "get", get)
    monkeypatch.setattr(dblp.time, "sleep", lambda seconds: None)

    result = dblp._get_with_retries("http://example.test", {}, "ctx")

    assert result is None
    assert calls["n"] == 5


def test_non_retryable_status_is_returned_as_is(monkeypatch):
    """A 404 (or any status outside the retry set) isn't dblp asking us to
    back off — it's a real answer, so the caller should get it immediately
    rather than have _get_with_retries spend retries on it."""
    not_found = FakeResponse(status_code=404)
    calls = {"n": 0}

    def get(*args, **kwargs):
        calls["n"] += 1
        return not_found

    monkeypatch.setattr(dblp.requests, "get", get)

    result = dblp._get_with_retries("http://example.test", {}, "ctx")

    assert result is not_found
    assert calls["n"] == 1
