class ApplicationError(Exception):
    def __init__(self, message: str):
        self.message = message

class PasswordRequirementError(ApplicationError):
    def __init__(self):
        super().__init__(
            message="Password must be at least 8 characters long, "
            "with only Latin letters and at least one digit or special character(!@#$%^&*)."
        )

class NotFoundError(ApplicationError):
    def __init__(self, spec: str = ""):
        super().__init__(
            message=f"{spec} Not Found"
        )

class WrongPasswordError(ApplicationError):
    def __init__(self):
        super().__init__(
            message=f"Wrong Password!"
        )

class AlreadyExistsError(ApplicationError):
    def __init__(self, spec: str = ""):
        super().__init__(
            message=f"{spec} already exists"
        )

class NotDirectoryError(ApplicationError):
    def __init__(self):
        super().__init__(
            message=f"Resource path is not directory"
        )