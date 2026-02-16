from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse

from cloud_storage.application.dto import MoveResourceDTO, UploadFileDTO, UserRegisterData
from cloud_storage.application.interactors import (
    CreateDirectoryInteractor,
    DeleteResourceInteractor,
    DownloadResourceInteractor,
    GetResourceInteractor,
    ListDirectoryInteractor,
    LoginUserInteractor,
    MoveResourceInteractor,
    RegisterUserInteractor,
    SearchResourceInteractor,
    UploadFileInteractor,
)
from cloud_storage.application.interfaces import SessionGateway

from .schemas import ResourceResponse, UserRegisterRequest

router = APIRouter(prefix="/api")


def get_session_id(request: Request) -> str:
    if not request.cookies.get("session_id", False):
        raise HTTPException(status_code=401)
    return request.cookies["session_id"]


@router.post("/sign-up")
@inject
async def register_user(data: Annotated[UserRegisterRequest, Form()], use_case: FromDishka[RegisterUserInteractor]):
    await use_case(register_data=UserRegisterData(login=data.login, password=data.password))
    return Response(status_code=200)


@router.post("/sign-in")
@inject
async def login_user_api(
    data: Annotated[UserRegisterRequest, Form()],
    use_case: FromDishka[LoginUserInteractor],
    session_gateway: FromDishka[SessionGateway],
):
    user_id = await use_case(login_data=UserRegisterData(login=data.login, password=data.password))

    session = await session_gateway.create(user_id=user_id)
    response = JSONResponse(content={"username": data.login})
    response.set_cookie(key="session_id", value=session.id, expires=session.expired_ts)
    return response


@router.post("/sign-out")
@inject
async def logout_user_api(session_gateway: FromDishka[SessionGateway], session_id: str = Depends(get_session_id)):
    await session_gateway.delete(session_id=session_id)
    response = Response(status_code=200)
    response.delete_cookie(key="session_id")
    return response


@router.post("/directory")
@inject
async def create_directory(
    path: str,
    use_case: FromDishka[CreateDirectoryInteractor],
    session_gateway: FromDishka[SessionGateway],
    session_id: str = Depends(get_session_id),
) -> ResourceResponse:
    user_id = await session_gateway.get_user_id(session_id=session_id)

    resource = await use_case(path=path, user_id=user_id)
    resource_response = ResourceResponse(path=str(resource.parent_path), name=resource.name, type=resource.type)
    return resource_response


@router.get("/resource")
@inject
async def get_resource(
    path: str,
    use_case: FromDishka[GetResourceInteractor],
    session_gateway: FromDishka[SessionGateway],
    session_id: str = Depends(get_session_id),
) -> ResourceResponse:
    user_id = await session_gateway.get_user_id(session_id=session_id)

    resource = await use_case(path=path, user_id=user_id)
    resource_response = ResourceResponse(
        path=str(resource.parent_path), name=resource.name, type=resource.type, size=resource.size
    )
    return resource_response


@router.delete("/resource")
@inject
async def delete_resource(
    path: str,
    use_case: FromDishka[DeleteResourceInteractor],
    session_gateway: FromDishka[SessionGateway],
    session_id: str = Depends(get_session_id),
) -> None:
    user_id = await session_gateway.get_user_id(session_id=session_id)

    await use_case(path=path, user_id=user_id)


@router.get("/resource/download/")
@inject
async def download_resource(
    path: str,
    use_case: FromDishka[DownloadResourceInteractor],
    session_gateway: FromDishka[SessionGateway],
    session_id: str = Depends(get_session_id),
) -> StreamingResponse:
    user_id = await session_gateway.get_user_id(session_id=session_id)

    file_stream = await use_case(path=path, user_id=user_id)
    return StreamingResponse(file_stream)


@router.get("/resource/move/")
@inject
async def move_resource(
    from_path: str,
    to_path: str,
    use_case: FromDishka[MoveResourceInteractor],
    session_gateway: FromDishka[SessionGateway],
    session_id: str = Depends(get_session_id),
) -> ResourceResponse:
    user_id = await session_gateway.get_user_id(session_id=session_id)

    resource = await use_case(data=MoveResourceDTO(user_id=user_id, current_path=from_path, target_path=to_path))
    resource_response = ResourceResponse(
        path=str(resource.parent_path), name=resource.name, type=resource.type, size=resource.size
    )
    return resource_response


@router.get("/resource/search/")
@inject
async def search_resource(
    query: str,
    use_case: FromDishka[SearchResourceInteractor],
    session_gateway: FromDishka[SessionGateway],
    session_id: str = Depends(get_session_id),
) -> list[ResourceResponse]:
    user_id = await session_gateway.get_user_id(session_id=session_id)

    resources = await use_case(resource_name=query, user_id=user_id)
    resource_responses = [
        ResourceResponse(path=str(res.parent_path), name=res.name, type=res.type, size=res.size) for res in resources
    ]
    return resource_responses


@router.post("/resource")
@inject
async def upload_resource(
    path: str,
    file: UploadFile,
    use_case: FromDishka[UploadFileInteractor],
    session_gateway: FromDishka[SessionGateway],
    session_id: str = Depends(get_session_id),
) -> ResourceResponse:
    user_id = await session_gateway.get_user_id(session_id=session_id)

    content = await file.read()
    resource = await use_case(data=UploadFileDTO(user_id=user_id, target_path=path + file.filename, content=content))
    resource_response = ResourceResponse(
        path=str(resource.parent_path), name=resource.name, type=resource.type, size=resource.size
    )
    return resource_response


@router.get("/directory")
@inject
async def list_directory(
    path: str,
    use_case: FromDishka[ListDirectoryInteractor],
    session_gateway: FromDishka[SessionGateway],
    session_id: str = Depends(get_session_id),
) -> list[ResourceResponse]:
    user_id = await session_gateway.get_user_id(session_id=session_id)

    resources = await use_case(path=path, user_id=user_id)
    resource_responses = [
        ResourceResponse(path=str(res.parent_path), name=res.name, type=res.type, size=res.size) for res in resources
    ]
    return resource_responses
