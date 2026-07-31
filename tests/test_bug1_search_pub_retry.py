"""Regression tests for the dblp.search_pub retry bug.

search_pub is supposed to retry up to 5 times when requests.get raises
(timeout, connection reset, dblp soft-ban) before giving up. A variable
typo (`timeOutCount3` at init vs `timeoutCount3` used in the except
branch) means the *first* failure crashes with an UnboundLocalError
instead of retrying — and since get_authors() calls search_pub outside
any try/except, that crash takes down the whole script, losing all
progress (authorList is only checkpointed after every year is fetched).
"""
import json

import dblp

from helpers import FakeResponse


def test_search_pub_succeeds_without_any_failure(monkeypatch):
    ok_response = FakeResponse(json_data={"result": {"hits": {}}})
    monkeypatch.setattr(dblp.requests, "get", lambda *a, **k: ok_response)

    result = json.loads(dblp.search_pub("conf/dsn/2023"))

    assert "hit" not in result["result"]["hits"]


def test_search_pub_retries_after_one_transient_failure(monkeypatch):
    """A single connection error should be retried, not crash the script."""
    ok_response = FakeResponse(json_data={"result": {"hits": {}}})
    calls = {"n": 0}

    def flaky_get(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("simulated transient network failure")
        return ok_response

    monkeypatch.setattr(dblp.requests, "get", flaky_get)

    result = json.loads(dblp.search_pub("conf/dsn/2023"))

    assert "hit" not in result["result"]["hits"]
    assert calls["n"] == 2, "expected exactly one retry after the single failure"


def test_search_pub_failure_does_not_raise_unboundlocalerror(monkeypatch):
    """Pins the exact reported bug: hitting the except branch must not
    itself crash on the undefined timeoutCount3/timeOutCount3 variable."""

    def always_fail(*args, **kwargs):
        raise ConnectionError("simulated network failure")

    monkeypatch.setattr(dblp.requests, "get", always_fail)

    try:
        dblp.search_pub("conf/dsn/2023")
    except UnboundLocalError as exc:
        raise AssertionError(
            f"search_pub crashed on its own retry bookkeeping instead of "
            f"retrying: {exc}"
        )
    except Exception:
        pass  # some other, intentional failure mode is fine for this test


def test_search_pub_fails_predictably_after_exhausting_retries(monkeypatch):
    """Even once the typo is fixed, if every attempt fails, `resp` is
    never assigned — `return resp.text` would still crash with an
    unrelated UnboundLocalError. The fix must give up cleanly (e.g.
    return None) so get_authors' existing try/except around json.loads
    can treat it as "no data for this year" instead of crashing."""

    def always_fail(*args, **kwargs):
        raise ConnectionError("simulated persistent network failure")

    monkeypatch.setattr(dblp.requests, "get", always_fail)

    try:
        result = dblp.search_pub("conf/dsn/2023")
    except (NameError, UnboundLocalError) as exc:
        raise AssertionError(
            f"search_pub crashed with {type(exc).__name__} after exhausting "
            f"retries instead of failing predictably: {exc}"
        )
    else:
        assert result is None
