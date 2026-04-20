from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

# 允许上传的文件扩展名。
# 这里我们主要看文件后缀，因为浏览器传过来的 content_type 不一定稳定。
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}


# 验证上传文件的格式
def validate_upload_file(upload_file: UploadFile) -> str:
    """
    校验上传文件是否符合要求。

    返回值：
    - 返回文件后缀（例如 .pdf），方便后续保存文件时复用。

    为什么单独拆一个函数：
    - 路由层就不用塞很多校验逻辑
    - 以后如果要新增 docx、csv，只改这里就行
    """

    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传的文件需要有文件名",
        )

    # 获取文件的后缀
    suffix = Path(upload_file.filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件后缀不符合要求，请上传pdf,txt,md文件",
        )

    return suffix


async def save_upload_file(upload_file: UploadFile) -> str:
    """
    把上传的文件保存到本地磁盘，并返回保存后的文件路径。

    设计说明：
    - 数据库里保留原始文件名，方便用户识别
    - 磁盘里使用 uuid 文件名，避免重名覆盖
    - 读取时按块写入，避免一次性把整个文件读进内存
    """

    suffix = validate_upload_file(upload_file)

    # 统一把上传文件放到 FILE_STORAGE_ROOT/uploads 目录下
    storage_dir = settings.BASE_DIR / settings.FILE_STORAGE_ROOT / "uploads"
    storage_dir.mkdir(parents=True, exist_ok=True)

    # 用 uuid 生成真正保存到磁盘上的文件名，避免同名文件冲突
    saved_filename = f"{uuid4().hex}{suffix}"
    saved_path = storage_dir / saved_filename

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    current_size = 0

    try:
        async with aiofiles.open(saved_path, "wb") as out_file:
            while True:
                # 每次读取 1MB，适合新手理解，也足够稳定
                chunk = await upload_file.read(1024 * 1024)
                if not chunk:
                    break

                current_size += len(chunk)

                # 文件超限时，立刻报错
                if current_size > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"文件大小不能超过 {settings.MAX_UPLOAD_SIZE_MB}MB。",
                    )

                await out_file.write(chunk)

    except HTTPException:
        # 如果是我们主动抛出的业务错误，尽量删除半截文件
        if saved_path.exists():
            saved_path.unlink()
        raise
    except Exception:
        # 如果是其他未知错误，也删除半截文件，避免磁盘里留下脏数据
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存文件失败，请稍后重试。",
        )
    finally:
        # 上传文件对象使用完后及时关闭
        await upload_file.close()

    return str(saved_path)
