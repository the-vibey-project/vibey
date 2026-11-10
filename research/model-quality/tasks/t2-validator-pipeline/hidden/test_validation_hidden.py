import pytest
from signup.form import SignupForm
from signup.service import SignupError, SignupService
from signup.validation import (
    ValidatorPipeline,
    default_pipeline,
    validate_age,
    validate_email,
    validate_username,
)


def form(username: str = "alice", email: str = "a@b.co", age: int = 30) -> SignupForm:
    return SignupForm(username, email, age)


def test_pipeline_runs_in_order_and_concatenates() -> None:
    pipeline = ValidatorPipeline()
    pipeline.add(lambda f: ["one", "two"]).add(lambda f: []).add(lambda f: ["three"])
    assert pipeline.run(form()) == ["one", "two", "three"]


def test_empty_pipeline_reports_nothing() -> None:
    assert ValidatorPipeline().run(form()) == []


def test_add_returns_the_pipeline() -> None:
    pipeline = ValidatorPipeline()
    assert pipeline.add(lambda f: []) is pipeline


@pytest.mark.parametrize("name", ["abc", "a_b_c", "A1" * 10, "user_99"])
def test_valid_usernames(name: str) -> None:
    assert validate_username(form(username=name)) == []


def test_username_length_errors() -> None:
    expected = ["username must be 3-20 characters"]
    assert validate_username(form(username="ab")) == expected
    assert validate_username(form(username="a" * 21)) == expected


def test_username_character_error() -> None:
    expected = ["username may only contain letters, digits and _"]
    assert validate_username(form(username="bad name")) == expected
    assert validate_username(form(username="caféx")) == expected


def test_username_can_fail_both_rules_in_order() -> None:
    assert validate_username(form(username="a-")) == [
        "username must be 3-20 characters",
        "username may only contain letters, digits and _",
    ]
    assert len(validate_username(form(username=""))) == 2


@pytest.mark.parametrize("email", ["a@b.co", "x.y@mail.example.org", "a@b.c.d"])
def test_valid_emails(email: str) -> None:
    assert validate_email(form(email=email)) == []


@pytest.mark.parametrize(
    "email", ["", "plain", "@b.co", "a@", "a@b", "a@.co", "a@b.", "a@@b.co", "a@b@c.co"]
)
def test_invalid_emails(email: str) -> None:
    assert validate_email(form(email=email)) == ["invalid email"]


def test_age_bounds() -> None:
    assert validate_age(form(age=13)) == []
    assert validate_age(form(age=120)) == []
    assert validate_age(form(age=12)) == ["age must be between 13 and 120"]
    assert validate_age(form(age=121)) == ["age must be between 13 and 120"]


def test_default_pipeline_collects_everything_in_order() -> None:
    errors = default_pipeline().run(SignupForm("a!", "nope", 3))
    assert errors == [
        "username must be 3-20 characters",
        "username may only contain letters, digits and _",
        "invalid email",
        "age must be between 13 and 120",
    ]


def test_default_pipeline_is_new_each_time() -> None:
    first = default_pipeline()
    first.add(lambda f: ["extra"])
    assert default_pipeline().run(form()) == []


def test_register_reports_all_errors() -> None:
    service = SignupService()
    with pytest.raises(SignupError) as info:
        service.register(SignupForm("x", "bad", 5))
    assert info.value.errors == [
        "username must be 3-20 characters",
        "invalid email",
        "age must be between 13 and 120",
    ]
    assert str(info.value) == "; ".join(info.value.errors)
    assert service.count() == 0


def test_register_success_and_duplicates() -> None:
    service = SignupService()
    user = service.register(form())
    assert (user.username, user.email, user.age) == ("alice", "a@b.co", 30)
    with pytest.raises(SignupError) as info:
        service.register(form(username="ALICE", email="z@z.zz"))
    assert info.value.errors == ["username already taken"]
    assert isinstance(info.value, ValueError)
    assert service.count() == 1


def test_validation_errors_come_before_duplicate_check() -> None:
    service = SignupService()
    service.register(form())
    with pytest.raises(SignupError) as info:
        service.register(form(username="alice", email="bad"))
    assert info.value.errors == ["invalid email"]
