def test_get_by_id_with_existing_user(user_repository, existing_user):
    user = user_repository.get_by_id(existing_user.id)
    assert user['id'] == existing_user.id
    assert user['username'] == existing_user.username
    
def test_get_by_id_with_nonexisting_user(user_repository, nonexisting_user):
    user = user_repository.get_by_id(nonexisting_user.id)
    assert user == None

def test_all_users_with_nonempty_db(user_repository, example_users):
    users = user_repository.all()
    assert len(users) == len(example_users)
    for loaded_user, example_user in zip(users, example_users):
        assert loaded_user['id'] == example_user.id
        assert loaded_user['username'] == example_user.username

def test_get_by_username_and_password_with_existing_user(user_repository, existing_user):
    user = user_repository.get_by_username_and_password(existing_user.username, existing_user.password)
    assert user['id'] == existing_user.id
    assert user['username'] == existing_user.username

def test_get_by_username_and_password_with_nonexisting_user(user_repository, nonexisting_user):
    user = user_repository.get_by_username_and_password(nonexisting_user.username, nonexisting_user.password)
    assert user == None