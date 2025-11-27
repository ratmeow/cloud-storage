from cloud_storage.application.interfaces import FileStorageGateway
from cloud_storage.config import MinioConfig
from aiobotocore.client import AioBaseClient
from botocore.exceptions import ClientError

class MinioGateway(FileStorageGateway):
    def __init__(self, client: AioBaseClient, config: MinioConfig):
        self._client = client
        self._bucket = config.bucket

    async def save_file(self, storage_path: str, content: bytes) -> None:
        await self._client.put_object(Bucket=self._bucket, Key=storage_path, Body=content)

    async def get_file(self, storage_path: str) -> bytes:
        resp = await self._client.get_object(Bucket=self._bucket, Key=storage_path)
        data = await resp["Body"].read()
        return data

    async def delete(self, storage_path: str) -> None:
        await self._client.delete_object(Bucket=self._bucket, Key=storage_path)
        if storage_path.endswith("/"):
            dir_objects = await self.list_directory_recursive(storage_path=storage_path, relative_response=False)
            for item in dir_objects:
                await self._client.delete_object(Bucket=self._bucket, Key=item)


    async def exists(self, storage_path: str) -> bool:
        try:
            await self._client.head_object(Bucket=self._bucket, Key=storage_path)
            return True
        except ClientError:
            resp = await self._client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=storage_path,
                MaxKeys=1,
            )

            return "Contents" in resp

    async def move(self, from_path: str, to_path: str) -> None:
        paginator = self._client.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=self._bucket, Prefix=from_path):
            for obj in page.get("Contents", []):
                old_key = obj["Key"]
                new_key = to_path + old_key[len(from_path):]

                await self._client.copy_object(
                    Bucket=self._bucket,
                    CopySource={"Bucket": self._bucket, "Key": old_key},
                    Key=new_key,
                )

                await self._client.delete_object(Bucket=self._bucket, Key=old_key)


    async def list_directory(self, storage_path: str) -> list[str]:
        kwargs = {"Bucket": self._bucket, "Prefix": storage_path, "Delimiter": "/"}
        resp = await self._client.list_objects_v2(**kwargs)
        results = []
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key == storage_path:
                continue
            results.append(key)
        for cp in resp.get("CommonPrefixes", []):
            current_prefix = cp.get("Prefix")
            results.append(current_prefix)
        return results

    async def get_file_size(self, storage_path: str) -> int:
        resp = await self._client.head_object(Bucket=self._bucket, Key=storage_path)
        return int(resp["ContentLength"])

    async def create_directory(self, storage_path: str) -> None:
        await self._client.put_object(Bucket=self._bucket, Key=storage_path, Body=b"")

    async def list_directory_recursive(self, storage_path: str, relative_response: bool = True) -> list[str]:
        results = []
        paginator = self._client.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=self._bucket, Prefix=storage_path):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key == storage_path:
                    continue
                if relative_response:
                    key = key[len(storage_path):]
                results.append(key)
        return results

