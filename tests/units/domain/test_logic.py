def test_user_create():
    user = User.create(login="test", hashed_password="hashed_password")

    assert user.login == "test"
    assert user.hashed_password == "hashed_password"

def test_directory_create():
    user = User.create(login="test", hashed_password="hashed_password")
