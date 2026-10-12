from utils.cursor import encode_cursor

DEFAULT_PAGE_SIZE = 20


def page_size(query: dict) -> int:
    return int(query.get("limit", DEFAULT_PAGE_SIZE))


def build_page(items: list, size: int, to_dict) -> dict:
    page = items[:size]
    is_last_page = len(items) <= size
    return {
        "data": [to_dict(item) for item in page],
        "limit": size,
        "cursor": None if is_last_page else encode_cursor(page[-1].id),
        "is_last_page": is_last_page,
    }
