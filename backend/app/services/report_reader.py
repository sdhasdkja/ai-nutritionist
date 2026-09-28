"""体检报告文件读取服务

支持三种文件：
- 文本类 (.txt/.md/.log)：直接解码（utf-8 优先，gbk 兜底）
- PDF (.pdf)：pymupdf 提取文本；扫描件（无文本层）自动渲染成图片走视觉模型转录
- 图片 (.jpg/.jpeg/.png/.bmp/.webp)：调用百炼视觉模型 qwen-vl-max 转录指标
"""
import base64
import logging
from typing import List, Optional, Tuple

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VISION_PAGES = 8  # 扫描件最多识别前8页，防止超大文件拖垮视觉接口

TEXT_EXTS = {".txt", ".md", ".log", ".csv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

MIME_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".bmp": "image/bmp", ".webp": "image/webp",
}


def read_report_file(filename: str, content: bytes) -> str:
    """根据文件类型提取报告文本"""
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件过大，请上传10MB以内的文件")
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        text = _read_pdf(content)
    elif ext in TEXT_EXTS:
        text = _read_text(content)
    elif ext in IMAGE_EXTS:
        text = _read_image(ext, content)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {ext or '(无后缀)'}，请上传 PDF、TXT 或图片文件",
        )

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="未能从文件中识别出内容，请检查文件或改用粘贴文本")

    logger.info("[报告读取] %s (%.1fKB) -> 提取 %d 字", ext, len(content) / 1024, len(text))
    return text.strip()


def _read_text(content: bytes) -> str:
    """文本文件解码"""
    for encoding in ("utf-8", "gbk", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="文本编码无法识别，请保存为 UTF-8 格式")


def _read_pdf(content: bytes) -> Optional[str]:
    """PDF 提取文本；扫描件（无文本层）回退到视觉模型转录"""
    import pymupdf

    try:
        with pymupdf.open(stream=content, filetype="pdf") as doc:
            text = "\n".join(p.get_text() for p in doc).strip()
            if text:
                return text
            # 无文本层 → 扫描件，逐页渲染成图片走视觉识别
            logger.info("[报告读取] PDF无文本层（扫描件），%d 页转视觉识别", len(doc))
            return _read_pdf_by_vision(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF 解析失败: {e}")


def _read_pdf_by_vision(doc) -> Optional[str]:
    """扫描件PDF：每页渲染为图片，一次性交给视觉模型转录"""
    import pymupdf

    pages = list(doc)[:MAX_VISION_PAGES]
    if not pages:
        return None

    images: List[Tuple[str, str]] = []  # (mime, base64)
    for page in pages:
        # 2倍缩放渲染（约144dpi），保证OCR清晰度；JPEG压缩控制体积
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
        jpg = pix.tobytes(output="jpeg", jpg_quality=85)
        images.append(("image/jpeg", base64.b64encode(jpg).decode()))

    if len(doc) > MAX_VISION_PAGES:
        logger.warning("[报告读取] PDF共%d页，仅识别前%d页", len(doc), MAX_VISION_PAGES)

    prompt = (
        f"这是一份体检报告扫描件（共{len(images)}页，按顺序提供）。"
        "请把所有检查项目和数值逐行完整转录出来，保持「项目名 数值 单位」的格式"
        "（例如：空腹血糖 6.8 mmol/L），按页用「--- 第N页 ---」分隔，"
        "不要遗漏数值，不要添加解释。如果图片不是体检报告，请直接说明内容是什么。"
    )
    return _vision_transcribe(images, prompt)


def _read_image(ext: str, content: bytes) -> Optional[str]:
    """图片：调用百炼视觉模型转录体检指标"""
    b64 = base64.b64encode(content).decode()
    mime = MIME_BY_EXT.get(ext, "image/jpeg")

    prompt = (
        "这是一份体检报告的照片。请把图片中的检查项目和数值逐行完整转录出来，"
        "保持「项目名 数值 单位」的格式（例如：空腹血糖 6.8 mmol/L），"
        "不要遗漏数值，不要添加解释。如果图片不是体检报告，请直接说明图片内容是什么。"
    )
    return _vision_transcribe([(mime, b64)], prompt)


def _vision_transcribe(images: List[Tuple[str, str]], prompt: str) -> Optional[str]:
    """调用视觉模型转录（支持多图一次调用）"""
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI

    content: list = [{"type": "text", "text": prompt}]
    for mime, b64 in images:
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

    llm = ChatOpenAI(
        model=settings.VISION_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0.1,
        max_retries=1,
    )
    try:
        response = llm.invoke([HumanMessage(content=content)])
        return response.content
    except Exception as e:
        logger.exception("视觉识别失败")
        raise HTTPException(status_code=502, detail=f"图片识别失败: {e}")
