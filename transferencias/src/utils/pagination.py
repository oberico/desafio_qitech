DEFAULT_PAGE_SIZE = 20


def page_size(query: dict) -> int:
    return int(query.get("limit", DEFAULT_PAGE_SIZE))


def build_page(items: list, size: int, to_dict, key_of) -> dict:
    page = items[:size]
    is_last_page = len(items) <= size
    return {
        "data": [to_dict(item) for item in page],
        "cursor": None if is_last_page else key_of(page[-1]),
        "is_last_page": is_last_page,
    }
