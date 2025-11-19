from cloud_storage.application.interfaces import Hasher
import bcrypt

class BcryptHasher(Hasher):
    def hash(self, text: str) -> str:
        return bcrypt.hashpw(text.encode(), bcrypt.gensalt()).decode()

    def verify_hash(self, text: str, hashed_text: str) -> bool:
        return bcrypt.checkpw(text.encode(), hashed_text.encode())