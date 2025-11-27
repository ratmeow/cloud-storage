from cloud_storage.application.interfaces import ArchiveGateway
import io
import zipfile

class ZipGateway(ArchiveGateway):
    async def archive(self, folder: list) -> bytes:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in folder:
                zipf.writestr(item[0], item[1])

        zip_buffer.seek(0)
        return zip_buffer.read()