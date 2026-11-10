The `library/` package holds a small in-memory book repository (`library/models.py`,
`library/repository.py`). Add pagination to it.

1. Create `library/pagination.py` with a frozen dataclass `Page` with fields `items: list`,
   `page: int`, `page_size: int`, `total: int`, `total_pages: int`, `has_next: bool`,
   `has_prev: bool`, and a function `paginate(items, page, page_size) -> Page`.
2. `paginate` takes any list. `page` is 1-based. It returns the slice for that page, `total` is
   `len(items)`, and `total_pages` is the number of pages needed (0 when `items` is empty).
   `has_next` is `page < total_pages`; `has_prev` is `page > 1`.
3. Validation: `page < 1` raises `ValueError`; `page_size` must be between 1 and 100 inclusive,
   otherwise raise `ValueError`.
4. A page beyond the last page is not an error: it has `items == []`, and `page` is echoed back.
5. Add a method `BookRepository.page(page=1, page_size=10, title_contains=None) -> Page` in
   `library/repository.py`. It paginates the books ordered by id. When `title_contains` is
   given, only books matching `search_title(title_contains)` are paginated.
6. The existing `add`, `get`, `all` and `search_title` behaviour must not change.

Check your work by running a short script that adds a few books and pages through them.
