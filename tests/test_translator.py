# File: tests/test_translator.py

import pytest
from braille_translator.translator_v1 import (
    BrailleTranslator,
    unicode_to_binary,
    binary_to_unicode,
    unicode_to_dots,
    dots_to_unicode,
)

# ——————————————————————————————————————————————————————————————
# 테스트에 사용할 모든 케이스
# ——————————————————————————————————————————————————————————————
ALL_TEXT_CASES = [
    "", "and", "hello", "the", "zigzag", "OpenAI",
    "The quick brown fox jumps over the lazy dog",
    "and hello", "for you", "the world", "of people", "in out",
    "123", "007", "2025", "42번", "3.14", "100%", "!", "?!", ".,;:",
    '"Hello?"', "(test)", "[OK]", "{ }", "@#&*",
    1, 2,
    "안녕", "한글", "감사합니다",
    "안녕하세요 여러분", "파이썬 점자 변환기 테스트",
    "Hello 안녕 123!", "Test 테스트, 42번!",
    "Python 3.11 출시되었습니다.", "OpenAI와 함께라면!",
    "Email: test@example.com", "URL: https://openai.com",
]

# ——————————————————————————————————————————————————————————————
# 유니코드 점자 문자열 → 6비트 셀 배열 변환 헬퍼
# ——————————————————————————————————————————————————————————————
def unicode_to_cells(uni: str) -> list[list[int]]:
    """
    unicode 점자 문자열을 가져와,
    각 문자를 6비트 리스트 [b0,b1,...,b5]로 분해한 뒤 배열로 리턴.
    """
    cells: list[list[int]] = []
    for ch in uni:
        code = ord(ch) - 0x2800
        bits = format(code, "06b")
        cells.append([int(b) for b in bits])
    return cells

# ——————————————————————————————————————————————————————————————
# 라운드트립 헬퍼
# ——————————————————————————————————————————————————————————————
def roundtrip_text(tr: BrailleTranslator, text: str, fmt: str) -> str:
    """
    fmt == "unicode" : text → unicode 점자 → 다시 text
    fmt == "binary"  : text → unicode 점자 → 셀 배열 → 다시 text
    """
    try:
        # 1) 먼저 항상 unicode 점자 형태로 변환
        uni = tr.text_to_braille(text, fmt="unicode")

        if fmt == "unicode":
            # 그대로 다시 디코딩
            restored = tr.braille_to_text(uni)
        else:
            # binary라면 셀 배열로 바꾼 뒤 유니코드로 바꾸고 디코딩
            cells = unicode_to_cells(uni)
            binary_str = "".join("".join(map(str, cell)) for cell in cells)
            unicode_str = binary_to_unicode(binary_str)
            restored = tr.braille_to_text(unicode_str)

        return restored
    except Exception as e:
        return f"[ERROR: {e}]"

# ——————————————————————————————————————————————————————————————
# Translator 인스턴스 재사용을 피하기 위해 fixture로 생성
# ——————————————————————————————————————————————————————————————
@pytest.fixture(scope="function")
def tr():
    # max_workers=1로 하면 병렬 프로세스가 하나라 디버깅하기 편합니다.
    translator = BrailleTranslator(max_workers=1)
    yield translator
    translator.shutdown()

# ——————————————————————————————————————————————————————————————
# 유니코드 포맷 라운드트립 테스트
# ——————————————————————————————————————————————————————————————
@pytest.mark.parametrize("text", ALL_TEXT_CASES)
def test_roundtrip_unicode(tr, text):
    restored = roundtrip_text(tr, text, fmt="unicode")
    assert restored.strip() == str(text).strip(), (
        f"Unicode round-trip 실패:\n"
        f"  입력:    {text!r}\n"
        f"  복원:    {restored!r}"
    )

# ——————————————————————————————————————————————————————————————
# 바이너리 포맷 라운드트립 테스트
# ——————————————————————————————————————————————————————————————
@pytest.mark.parametrize("text", ALL_TEXT_CASES)
def test_roundtrip_binary(tr, text):
    restored = roundtrip_text(tr, text, fmt="binary")
    assert restored.strip() == str(text).strip(), (
        f"Binary round-trip 실패:\n"
        f"  입력:    {text!r}\n"
        f"  복원:    {restored!r}"
    )