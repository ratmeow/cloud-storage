import logging
from logging import FileHandler


class OverWritingFileHandler(FileHandler):
    def __init__(self, filename, max_bytes):
        super().__init__(filename=filename, mode="w")
        self.max_bytes = max_bytes

    def emit(self, record):
        if self.stream.tell() >= self.max_bytes:
            self.stream.seek(0)
            self.stream.truncate()
        super().emit(record=record)


def setup_package_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(asctime)s - [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M",
        handlers=[
            OverWritingFileHandler(
                filename="cloud.log",
                max_bytes=5 * 1024 * 1024,
            )
        ],
    )
