# -*- coding: utf-8 -*-
"""
【 V5 통합 점자 번역 시스템 테스트 코드 - 최종 완성본 】
"""
import pytest
import os
from pathlib import Path

# --- 테스트 대상 모듈 임포트 ---
# 【수정】 __init__.py를 통해 패키지에서 직접 클래스를 가져옵니다.
from braille_translator import (
    BrailleTranslator,
    InputFormatDetector,
    LanguageDetector,
    LanguageType,
    HAS_IMAGE_SUPPORT
)

try:
    import cv2
    import numpy as np
except ImportError:
    pass

# ============================================================
# ✨ 테스트 케이스 선언부
# ============================================================

ROUND_TRIP_TEXT_CASES = [
    "파이썬은 재미있는 프로그래밍 언어입니다.",
    "Braille translation using Liblouis is powerful.",
    "2025년 6월 19일, AI가 코드를 작성합니다.",
]
IMAGE_ROUND_TRIP_TEXT = "이미지 왕복 테스트 문장입니다."

# ============================================================
# ✨ 테스트 코드 실행부
# ============================================================

@pytest.fixture(scope="module")
def translator():
    """테스트 전체에서 사용할 BrailleTranslator 인스턴스를 생성합니다."""
    return BrailleTranslator(table_dir="tables")

@pytest.fixture(scope="module")
def lang_detector():
    """LanguageDetector 인스턴스를 생성합니다."""
    return LanguageDetector()

@pytest.fixture(scope="module", autouse=True)
def setup_test_directory():
    """테스트 결과물 저장 디렉토리를 생성합니다."""
    Path("tests/test_v5").mkdir(exist_ok=True)


# --- 컴포넌트 단위 테스트 ---

class TestHelperClasses:
    """InputFormatDetector와 LanguageDetector 클래스를 테스트합니다."""
    def test_input_format_detector(self, tmp_path: Path):
        img_file = tmp_path / "test.png"
        img_file.touch()
        test_data = {
            "text": "일반 텍스트", "unicode": "⠁⠃⠉", "dots": "1-2-3 4-5-6",
            "binary": "000001000011001001", "image": str(img_file)
        }
        for expected, data in test_data.items():
            assert InputFormatDetector.detect_input_type(data) == expected

    def test_language_detector(self, lang_detector: LanguageDetector):
        assert lang_detector.detect_language("안녕하세요") == LanguageType.KOREAN
        assert lang_detector.detect_language("Hello World 안녕하세요") == LanguageType.MIXED

# --- 통합 번역기 테스트 ---

class TestBrailleTranslator:
    """BrailleTranslator의 핵심 통합 기능들을 테스트합니다."""

    def test_unified_translation(self, translator: BrailleTranslator):
        text = "test 123"
        result = translator.unified_translate(text, generate_image=False)
        assert result.success
        assert result.braille_unicode == "⠞⠑⠎⠞ ⠼⠁⠃⠉"
        assert result.language_detected == "mixed"

    @pytest.mark.parametrize("text", ROUND_TRIP_TEXT_CASES)
    def test_e2e_round_trip(self, translator: BrailleTranslator, text):
        """텍스트-점자-텍스트 왕복 변환(E2E)을 검증합니다."""
        result = translator.unified_translate(text, generate_image=False)
        assert result.success
        restored_text, _ = translator.unified_restore(result.braille_unicode)
        assert restored_text == text

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="이미지 처리 라이브러리가 필요합니다.")
    def test_image_round_trip(self, translator: BrailleTranslator):
        """이미지 생성 및 복원 왕복 테스트."""
        text = IMAGE_ROUND_TRIP_TEXT
        result = translator.unified_translate(text, generate_image=True, image_output_dir="tests/test_v5")
        assert result.success and result.image_path and os.path.exists(result.image_path)
        
        restored_text, detected_type = translator.unified_restore(result.image_path)
        assert detected_type == "image"
        assert any(word in restored_text for word in text.split())

    def test_statistics(self, translator: BrailleTranslator):
        """통계 기능 테스트"""
        stats_translator = BrailleTranslator(table_dir="tables")
        assert stats_translator.get_statistics()['total_translations'] == 0
        stats_translator.unified_translate("첫 번째 번역")
        stats_translator.unified_translate("Second translation")
        stats = stats_translator.get_statistics()
        assert stats['total_translations'] == 2
        assert stats['language_distribution'] == {'korean': 1, 'english': 1}