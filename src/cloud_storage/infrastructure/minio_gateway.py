from typing import AsyncIterator

from aiobotocore.client import AioBaseClient
from botocore.exceptions import ClientError

from cloud_storage.config import MinioConfig
from cloud_storage.domain.value_objects import Path


class MinioGateway:
    def __init__(self, client: AioBaseClient, config: MinioConfig):
        self._client = client
        self._bucket = config.bucket
        self._chunk_size = 64 * 1024

    async def save_file(self, path: Path, content: bytes) -> None:
        await self._create_parents(path=path)
        await self._client.put_object(Bucket=self._bucket, Key=str(path), Body=content)

    async def get_file(self, path: Path) -> bytes:
        resp = await self._client.get_object(Bucket=self._bucket, Key=str(path))
        data = await resp["Body"].read()
        return data

    async def get_file_stream(self, path: Path) -> AsyncIterator[bytes]:
        resp = await self._client.get_object(Bucket=self._bucket, Key=str(path))
        body = resp["Body"]
        while True:
            chunk = await body.read(self._chunk_size)
            if not chunk:
                break
            yield chunk

    async def delete(self, path: Path) -> None:
        await self._client.delete_object(Bucket=self._bucket, Key=str(path))
        if path.is_directory:
            dir_objects = await self.list_directory_recursive(path=path)
            for item in dir_objects:
                await self._client.delete_object(Bucket=self._bucket, Key=str(item))

    async def exists(self, path: Path) -> bool:
        try:
            await self._client.head_object(Bucket=self._bucket, Key=str(path))
            return True
        except ClientError:
            return False

    async def move(self, from_path: Path, to_path: Path) -> None:
        paginator = self._client.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=self._bucket, Prefix=str(from_path)):
            for obj in page.get("Contents", []):
                old_key = Path(obj["Key"])
                new_key = to_path
                if from_path.is_directory:
                    new_key = to_path.join(old_key.relative_to(base=from_path))

                await self._client.copy_object(
                    Bucket=self._bucket,
                    CopySource={"Bucket": self._bucket, "Key": str(old_key)},
                    Key=str(new_key),
                )

                await self._client.delete_object(Bucket=self._bucket, Key=str(old_key))

    async def list_directory(self, path: Path) -> list[Path]:
        kwargs = {"Bucket": self._bucket, "Prefix": str(path), "Delimiter": "/"}
        resp = await self._client.list_objects_v2(**kwargs)
        results = []
        for obj in resp.get("Contents", []):
            key = Path(obj["Key"])
            if key == path:
                continue
            results.append(key)
        for cp in resp.get("CommonPrefixes", []):
            current_prefix = cp.get("Prefix")
            results.append(Path(current_prefix))
        return results

    async def get_file_size(self, path: Path) -> int:
        resp = await self._client.head_object(Bucket=self._bucket, Key=str(path))
        return int(resp["ContentLength"])

    async def create_directory(self, path: Path) -> None:
        await self._create_parents(path=path)
        await self._client.put_object(Bucket=self._bucket, Key=str(path), Body=b"")

    async def list_directory_recursive(self, path: Path) -> list[Path]:
        results = []
        paginator = self._client.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=self._bucket, Prefix=str(path)):
            for obj in page.get("Contents", []):
                key = Path(obj["Key"])
                if key == path:
                    continue
                results.append(key)
        return results

    async def _create_parents(self, path: Path) -> None:
        current_path = path.parent
        while not current_path.is_root:
            if await self.exists(path=current_path):
                break
            await self.create_directory(path=current_path)
            current_path = current_path.parent
