from pydantic import BaseModel


class UserRegisterRequest(BaseModel):
    login: str
    password: str


class ResourceResponse(BaseModel):
    path: str
    name: str
    type: str
    size: int | None = None
