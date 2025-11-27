import bcrypt


class BcryptHasher:
    def hash(self, text: str) -> str:
        return bcrypt.hashpw(text.encode(), bcrypt.gensalt()).decode()

    def verify_hash(self, original_text: str, hashed_text: str) -> bool:
        return bcrypt.checkpw(original_text.encode(), hashed_text.encode())
