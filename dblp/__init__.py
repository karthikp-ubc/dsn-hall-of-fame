import json
import time
import requests

DBLP_BASE_URL = 'http://dblp.uni-trier.de/'
DBLP_AUTHOR_SEARCH_URL2 = DBLP_BASE_URL + 'search/author/api'
DBLP_PUBL_SEARCH_URL = DBLP_BASE_URL + 'search/publ/api'

def _get_with_retries(url, params, context):
    """GET `url` with `params`, retrying up to 5 times if requests.get
    raises (timeout, connection reset, etc) or dblp responds with a
    rate-limit/server-error status (429/5xx). Unlike outright request
    failures, a 429 means dblp is asking us to slow down, so those
    retries back off with an increasing delay instead of firing right
    back. Returns the response, or None if every attempt failed.
    """
    timeoutCount = 0
    backoff = 5
    while True:
        try:
            resp = requests.get(url, params=params)
        except Exception:
            resp = None

        status = getattr(resp, "status_code", 200) if resp is not None else None

        if resp is not None and status not in (429, 500, 502, 503, 504):
            return resp

        timeoutCount += 1
        if timeoutCount >= 5:
            print("ERROR: failed to connect to DBLP 5+ times for" + str(context) + ", skipping")
            return None

        if status == 429:
            print(f"WARNING: dblp rate-limited us for {context}, backing off {backoff}s (attempt {timeoutCount}/5)")
            time.sleep(backoff)
            backoff *= 2
        elif status is not None:
            print(f"WARNING: dblp returned status {status} for {context}, retrying (attempt {timeoutCount}/5)")

def search_pub(pub_str):
    """Search dblp for publications matching `pub_str` (e.g. 'conf/dsn/2023').

    dblp's search API caps each response at 100 hits regardless of the
    requested `h`, so this pages through with the `f` offset parameter
    until all hits are collected, then returns them merged into a single
    JSON-encoded string shaped like a single-page response, so callers
    don't need to know about the pagination. Returns None if the first
    page can't be fetched after retrying.
    """
    page_size = 100
    first = 0
    total = None
    all_hits = []

    while True:
        resp = _get_with_retries(
            DBLP_PUBL_SEARCH_URL,
            {'q': pub_str, 'format': 'json', 'h': page_size, 'f': first},
            pub_str,
        )
        if resp is None:
            return None

        try:
            hits = json.loads(resp.text)["result"]["hits"]
        except (ValueError, KeyError, TypeError):
            return None

        if total is None:
            total = int(hits.get("@total", 0))

        all_hits.extend(hits.get("hit", []))

        first += page_size
        if first >= total or "hit" not in hits:
            break

        time.sleep(1)  # be polite to dblp between pages of the same year

    merged_hits = {
        "@total": str(total),
        "@sent": str(len(all_hits)),
        "@first": "0",
    }
    if all_hits:
        merged_hits["hit"] = all_hits

    return json.dumps({"result": {"hits": merged_hits}})

def get_affiliation(pid, author_str):
    """Look up `pid`'s affiliation by searching dblp for `author_str` and
    matching the pid embedded in each hit's dblp profile URL. Returns ""
    if no affiliation is found, including when dblp can't be reached
    after retrying, or the response can't be parsed.
    """
    resp = _get_with_retries(
        DBLP_AUTHOR_SEARCH_URL2, {'q': author_str, 'format': 'json', 'h': 1000}, author_str
    )
    if resp is None:
        return ""

    try:
        hits = json.loads(resp.text)["result"]["hits"]
    except (ValueError, KeyError, TypeError):
        return ""

    affiliation = None
    for hit in hits.get("hit", []):
        if "info" in hit:
            if "author" in hit["info"]:
                if "aliases" in hit["info"]:
                    for alias in hit["info"]["aliases"]["alias"]:
                        # print(alias)
                        pass

                # find pid -- which is on the url
                if "url" in hit["info"]:
                    if "https://dblp.org/pid" in hit["info"]["url"]:
                        xx = hit["info"]["url"][21:]
                        # print(xx)

                        if xx == pid:
                            if "notes" in hit["info"]:
                                note = hit["info"]["notes"]["note"]
                                # if the author has multiple notes
                                if isinstance(note, list):
                                    for text in note:
                                        if text["@type"] == "affiliation":
                                            affiliation = text["text"]
                                        # if there is more than one entry, we choose the first one
                                        if affiliation is not None: break

                                if "@type" in note:
                                    if note["@type"] == "affiliation":
                                        affiliation = note["text"]

                if affiliation is not None:
                    break

    return "" if affiliation is None else affiliation
