import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class ParsedSection:
    """
    解析后的文本片段。

    source_number 的含义：
    - 对 PDF：表示页码
    - 对 TXT / MD：表示段号

    这里为了少改表结构，先统一复用到后面的 page_number 字段里。
    """

    source_number: int | None
    text: str


def parse_document_file(file_path: str) -> list[ParsedSection]:
    """
    根据文件后缀，选择不同的解析方式。
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(path)

    if suffix in {".md", ".txt"}:
        return _parse_text_file(path)

    raise ValueError(f"暂不支持解析该文件类型: {suffix}")


def _parse_pdf(path: Path) -> list[ParsedSection]:
    """
    解析 PDF 文件。

    设计思路：
    - 一页对应一个 ParsedSection
    - 这样后面切块时，chunk 仍然知道自己来自哪一页
    """
    reader = PdfReader(str(path))
    sections: list[ParsedSection] = []

    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        cleaned_text = _clean_text(raw_text)

        # 空页就跳过，不生成 section
        if not cleaned_text:
            continue

        sections.append(
            ParsedSection(
                source_number=page_number,
                text=cleaned_text,
            )
        )

    return sections


def _parse_text_file(path: Path) -> list[ParsedSection]:
    """
    解析 txt / md 文件。
    这里先采用一个简单版本：
    - 先把整个文件读出来
    - 再按“空行”切成多个段落
    - 每一段给一个段号
    """

    raw_text = _read_text_with_fallback(path)
    cleaned_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # 按空行切分段落
    paragraphs = re.split(r"\n\s*\n", cleaned_text)

    sections: list[ParsedSection] = []

    for index, paragraph in enumerate(paragraphs, start=1):
        paragraph_text = _clean_text(paragraph)
        if not paragraph_text:
            continue

        sections.append(
            ParsedSection(
                source_number=index,
                text=paragraph_text,
            )
        )

    return sections


def _read_text_with_fallback(path: Path) -> str:
    """
    读取文本文件时做一个简单的编码兜底。

    原因：
    - 有些 txt / md 是 utf-8
    - 有些 Windows 环境下的文本文件可能是 gb18030
    """
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError("文本文件编码无法识别，暂时只支持 utf-8 / utf-8-sig / gb18030。")


def _clean_text(text: str) -> str:
    """
    做最基础的文本清洗。

    当前只做两件事：
    - 去掉首尾空白
    - 把连续空白压缩得更稳定一些，方便后续切块
    """
    text = text.strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
