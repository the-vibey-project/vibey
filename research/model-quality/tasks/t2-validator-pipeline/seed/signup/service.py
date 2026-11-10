from signup.form import SignupForm, User


class SignupError(ValueError):
    """Raised when a signup is refused. `errors` lists the reasons."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


class SignupService:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def register(self, form: SignupForm) -> User:
        if not 3 <= len(form.username) <= 20:
            raise SignupError(["username must be 3-20 characters"])
        if not form.username.replace("_", "").isalnum():
            raise SignupError(["username may only contain letters, digits and _"])
        if form.email.count("@") != 1:
            raise SignupError(["invalid email"])
        if not 13 <= form.age <= 120:
            raise SignupError(["age must be between 13 and 120"])
        key = form.username.lower()
        if key in self._users:
            raise SignupError(["username already taken"])
        user = User(form.username, form.email, form.age)
        self._users[key] = user
        return user

    def count(self) -> int:
        return len(self._users)
