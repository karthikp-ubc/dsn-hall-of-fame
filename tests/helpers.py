import json


class FakeResponse:
    """Stand-in for requests.Response, exposing the .text/.content attrs
    that dblp/__init__.py actually reads."""

    def __init__(self, json_data=None, text=None):
        if json_data is not None:
            self.text = json.dumps(json_data)
        else:
            self.text = text if text is not None else ""
        self.content = self.text.encode("utf-8")


def make_hit(n, venue="DSN", year=2023, pages="10-20", solo_author=True):
    """Build a fake dblp publ-search hit (the {'info': {...}} shape) for a
    plausible main-track DSN paper."""
    key = f"conf/dsn/Author{n}{str(year)[-2:]}"
    doi = f"10.1109/DSN.{year}.{1000 + n}"
    if solo_author:
        authors = {"author": {"@pid": f"00/{n}", "text": f"Author {n}"}}
    else:
        authors = {
            "author": [
                {"@pid": f"00/{n}", "text": f"Author {n}"},
                {"@pid": f"01/{n}", "text": f"Coauthor {n}"},
            ]
        }
    return {
        "info": {
            "title": f"Paper {n}",
            "venue": venue,
            "pages": pages,
            "year": str(year),
            "type": "Conference and Workshop Papers",
            "doi": doi,
            "key": key,
            "authors": authors,
        }
    }
