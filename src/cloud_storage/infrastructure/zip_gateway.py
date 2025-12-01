import io
import zipfile
from typing import AsyncIterator

import asynczipstream

from cloud_storage.domain.value_objects import Path


class ZipGateway:
    async def archive(self, files: list[tuple[Path, bytes]]) -> bytes:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in files:
                zipf.writestr(str(item[0]), item[1])

        zip_buffer.seek(0)
        return zip_buffer.read()

    def archive_stream(self, files: AsyncIterator[tuple[Path, AsyncIterator[bytes]]]) -> AsyncIterator[bytes]:
        z = asynczipstream.ZipFile()

        async def _streamer() -> AsyncIterator[bytes]:
            async for rel_path, body_iter in files:
                z.write_iter(str(rel_path), body_iter)

            async for chunk in z:
                yield chunk

        return _streamer()
