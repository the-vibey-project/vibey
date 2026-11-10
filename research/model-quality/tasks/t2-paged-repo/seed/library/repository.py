from library.models import Book


class BookRepository:
    """In-memory store of books. Ids are assigned from 1 in insertion order."""

    def __init__(self) -> None:
        self._books: dict[int, Book] = {}
        self._next_id = 1

    def add(self, title: str, author: str) -> Book:
        book = Book(self._next_id, title, author)
        self._books[book.id] = book
        self._next_id += 1
        return book

    def get(self, book_id: int) -> Book:
        return self._books[book_id]

    def all(self) -> list[Book]:
        return sorted(self._books.values(), key=lambda book: book.id)

    def search_title(self, text: str) -> list[Book]:
        needle = text.lower()
        return [book for book in self.all() if needle in book.title.lower()]
