from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True)
class UploadImage:
    """已驗證的影像檔案串流，避免將整批照片讀入記憶體。"""

    filename: str
    stream: BinaryIO
    content_type: str
    size: int
