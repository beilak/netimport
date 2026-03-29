from good_example.entities import User


def test_user_stores_name() -> None:
    user = User(name="test")

    assert user.name == "test"
