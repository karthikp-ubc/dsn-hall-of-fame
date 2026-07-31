"""Regression tests for dblp.get_affiliation — matches a pid against the
dblp author-search results and pulls out the affiliation note, if any."""
import dblp

from helpers import FakeResponse


def _hits(entries):
    return {"result": {"hits": {"hit": entries}}}


def test_returns_matching_authors_affiliation(monkeypatch):
    body = _hits(
        [
            {
                "info": {
                    "author": "Jane Doe",
                    "url": "https://dblp.org/pid/00/1",
                    "notes": {"note": {"@type": "affiliation", "text": "MIT"}},
                }
            }
        ]
    )
    monkeypatch.setattr(dblp.requests, "get", lambda *a, **k: FakeResponse(json_data=body))

    assert dblp.get_affiliation("00/1", "Jane Doe") == "MIT"


def test_picks_affiliation_note_out_of_a_list_of_notes(monkeypatch):
    body = _hits(
        [
            {
                "info": {
                    "author": "Jane Doe",
                    "url": "https://dblp.org/pid/00/1",
                    "notes": {
                        "note": [
                            {"@type": "homepage", "text": "https://example.com"},
                            {"@type": "affiliation", "text": "MIT"},
                        ]
                    },
                }
            }
        ]
    )
    monkeypatch.setattr(dblp.requests, "get", lambda *a, **k: FakeResponse(json_data=body))

    assert dblp.get_affiliation("00/1", "Jane Doe") == "MIT"


def test_returns_empty_string_when_pid_not_found(monkeypatch):
    body = _hits(
        [{"info": {"author": "Someone Else", "url": "https://dblp.org/pid/99/9"}}]
    )
    monkeypatch.setattr(dblp.requests, "get", lambda *a, **k: FakeResponse(json_data=body))

    assert dblp.get_affiliation("00/1", "Jane Doe") == ""


def test_returns_empty_string_when_no_notes_present(monkeypatch):
    body = _hits([{"info": {"author": "Jane Doe", "url": "https://dblp.org/pid/00/1"}}])
    monkeypatch.setattr(dblp.requests, "get", lambda *a, **k: FakeResponse(json_data=body))

    assert dblp.get_affiliation("00/1", "Jane Doe") == ""


def test_returns_empty_string_when_there_are_zero_hits(monkeypatch):
    # Real dblp omits the "hit" key entirely when a search matches nobody
    # (e.g. @total=0) -- hits["hit"] used to raise a bare KeyError here.
    body = {"result": {"hits": {"@total": "0"}}}
    monkeypatch.setattr(dblp.requests, "get", lambda *a, **k: FakeResponse(json_data=body))

    assert dblp.get_affiliation("00/1", "Jane Doe") == ""


def test_returns_empty_string_on_malformed_json(monkeypatch):
    monkeypatch.setattr(dblp.requests, "get", lambda *a, **k: FakeResponse(text="not json"))

    assert dblp.get_affiliation("00/1", "Jane Doe") == ""


def test_retries_after_one_transient_failure(monkeypatch):
    body = _hits(
        [
            {
                "info": {
                    "author": "Jane Doe",
                    "url": "https://dblp.org/pid/00/1",
                    "notes": {"note": {"@type": "affiliation", "text": "MIT"}},
                }
            }
        ]
    )
    ok_response = FakeResponse(json_data=body)
    calls = {"n": 0}

    def flaky_get(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("simulated transient network failure")
        return ok_response

    monkeypatch.setattr(dblp.requests, "get", flaky_get)

    assert dblp.get_affiliation("00/1", "Jane Doe") == "MIT"
    assert calls["n"] == 2


def test_returns_empty_string_when_search_exhausts_retries(monkeypatch):
    # Previously: `resp` was never assigned once retries were exhausted,
    # so json.loads(resp.text) crashed with an UnboundLocalError.
    def always_fail(*args, **kwargs):
        raise ConnectionError("simulated persistent network failure")

    monkeypatch.setattr(dblp.requests, "get", always_fail)

    assert dblp.get_affiliation("00/1", "Jane Doe") == ""
