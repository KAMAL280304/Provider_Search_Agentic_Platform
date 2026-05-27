from app.db.repositories.user_repo import UserRepository


class UserService:
    def __init__(self):
        self.repo = UserRepository()

    def get_user(self, user_id: str):
        user = self.repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        return user
