import io
import zipfile
from cloud_storage.domain.value_objects import Path

class ZipGateway:
    async def archive(self, folder: list[tuple[Path, bytes]]) -> bytes:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in folder:
                zipf.writestr(str(item[0]), item[1])

        zip_buffer.seek(0)
        return zip_buffer.read()