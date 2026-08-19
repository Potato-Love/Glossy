import asyncio
import unittest

from app.schemas import MAX_TRANSLATE_TEXT_CHARS
from app.services.uploaded_text import (
    count_words,
    extract_text_from_upload,
    split_into_paragraphs,
)


class DummyUpload:
    def __init__(self, filename: str, payload: bytes, content_type: str = "text/plain") -> None:
        self.filename = filename
        self._payload = payload
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._payload


class UploadedTextTest(unittest.TestCase):
    def test_extract_utf8_text(self) -> None:
        upload = DummyUpload("sample.txt", "글로시 MVP\nQA".encode())

        text = asyncio.run(extract_text_from_upload(upload))

        self.assertEqual(text, "글로시 MVP\nQA")

    def test_split_paragraphs(self) -> None:
        paragraphs = split_into_paragraphs("첫 문단입니다.\n\n두 번째 문단입니다.")

        self.assertEqual(paragraphs, ["첫 문단입니다.", "두 번째 문단입니다."])

    def test_split_long_paragraph_chunks_under_translate_limit(self) -> None:
        paragraphs = split_into_paragraphs("가" * (MAX_TRANSLATE_TEXT_CHARS + 50))

        self.assertEqual(len(paragraphs), 2)
        self.assertLessEqual(max(len(paragraph) for paragraph in paragraphs), MAX_TRANSLATE_TEXT_CHARS)

    def test_count_words(self) -> None:
        self.assertEqual(count_words("글로시 MVP QA"), 3)


if __name__ == "__main__":
    unittest.main()
