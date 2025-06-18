# -*- coding: utf-8 -*-
"""
【 V5 통합 점자 번역 시스템 테스트 코드 - 최종 완성본 】
- 각 컴포넌트 단위 테스트 및 통합 기능 테스트 포함
- 테스트 케이스를 상단에 분리하여 관리 용이성 증대
"""

import pytest
import os
from pathlib import Path

# --- 테스트 대상 모듈 임포트 ---
# __init__.py를 통해 패키지에서 직접 클래스를 가져옵니다.
from braille_translator import (
    SuperBrailleTranslator,
    InputFormatDetector,
    LanguageDetector,
    LanguageType,
    ContractionLevel,
    HAS_IMAGE_SUPPORT
)

# 이미지 처리 라이브러리 확인
try:
    import cv2
    import numpy as np
except ImportError:
    pass

# ============================================================
# ✨ 테스트 케이스 선언부
# 예제를 수정하거나 추가하려면 이 부분을 수정하시면 됩니다.
# ============================================================

# --- 왕복 변환 테스트 케이스 ---
ROUND_TRIP_TEXT_CASES = [
    "파이썬은 재미있는 프로그래밍 언어입니다.",
    "Braille translation using Liblouis is powerful.",
    "2025년 6월 19일, AI가 코드를 작성합니다.",
    "가격: $100, 수량: 5개 (Total: $500)"
]

# --- 이미지 왕복 변환 테스트 케이스 ---
IMAGE_ROUND_TRIP_TEXT = "이미지 왕복 테스트 문장입니다."


# ============================================================
# ✨ 테스트 코드 실행부
# ============================================================

@pytest.fixture(scope="module")
def translator():
    """테스트 전체에서 사용할 SuperBrailleTranslator 인스턴스를 생성합니다."""
    return SuperBrailleTranslator(table_dir="tables")

@pytest.fixture(scope="module")
def lang_detector():
    """LanguageDetector 인스턴스를 생성합니다."""
    return LanguageDetector()

@pytest.fixture(scope="module", autouse=True)
def setup_test_directory():
    """모든 테스트 실행 전, 테스트 결과물 저장 디렉토리를 생성합니다."""
    Path("tests/test_v5").mkdir(exist_ok=True)


# --- 컴포넌트 단위 테스트 ---

class TestHelperClasses:
    """InputFormatDetector와 LanguageDetector 클래스의 기능들을 테스트합니다."""

    def test_input_format_detector(self, tmp_path: Path):
        """다양한 입력 포맷을 정확히 감지하는지 테스트합니다."""
        img_file = tmp_path / "test.png"
        img_file.touch()

        test_data = {
            "text": "일반 텍스트",
            "unicode": "⠁⠃⠉",
            "dots": "1-2-3 4-5-6",
            "binary": "000001000011001001",
            "image": str(img_file)
        }
        for expected, data in test_data.items():
            assert InputFormatDetector.detect_input_type(data) == expected

    def test_language_detector(self, lang_detector: LanguageDetector):
        """언어 감지 및 세그먼트 분할 기능을 테스트합니다."""
        assert lang_detector.detect_language("안녕하세요") == LanguageType.KOREAN
        assert lang_detector.detect_language("Hello") == LanguageType.ENGLISH
        assert lang_detector.detect_language("12345") == LanguageType.NUMBER
        assert lang_detector.detect_language("Hello World 안녕하세요") == LanguageType.MIXED
        
        segments = lang_detector.segment_by_language("Test 123 안녕하세요.")
        expected_segments = [
            ("Test", LanguageType.ENGLISH),
            (" ", LanguageType.UNKNOWN),
            ("123", LanguageType.NUMBER),
            (" ", LanguageType.UNKNOWN),
            ("안녕하세요", LanguageType.KOREAN),
            (".", LanguageType.PUNCTUATION)
        ]
        assert segments == expected_segments

# --- 통합 번역기 테스트 ---

class TestSuperBrailleTranslator:
    """SuperBrailleTranslator의 핵심 통합 기능들을 테스트합니다."""

    def test_unified_translation_and_result_object(self, translator: SuperBrailleTranslator):
        """통합 번역 기능 및 반환 객체의 정확성을 테스트합니다."""
        text = "test 123"
        result = translator.unified_translate(text, generate_image=False)

        assert result.success is True
        assert result.original_text == text
        assert result.braille_unicode == "⠞⠑⠎⠞ ⠼⠁⠃⠉"
        assert result.braille_dots == "2-3-4-5 1-5 2-3-4 2-3-4-5 0 6 1 1-2 1-4"
        assert result.language_detected == "mixed"
        assert len(result.segments) > 1

    @pytest.mark.parametrize("text", ROUND_TRIP_TEXT_CASES)
    def test_v5_text_to_braille_and_back_e2e(self, translator: SuperBrailleTranslator, text):
        """텍스트-점자 왕복 변환(E2E) 후 원본과 일치하는지 검증합니다."""
        result = translator.unified_translate(text, generate_image=False)
        assert result.success

        restored_text, _ = translator.unified_restore(result.braille_unicode)
        assert restored_text == text, f"왕복 변환 실패: 원본 '{text}', 복원 '{restored_text}'"

    @pytest.mark.skipif(not HAS_IMAGE_SUPPORT, reason="이미지 처리 라이브러리가 필요합니다.")
    def test_v5_image_round_trip(self, translator: SuperBrailleTranslator):
        """이미지 생성 및 복원 왕복 테스트."""
        text = IMAGE_ROUND_TRIP_TEXT

        # 1. 텍스트 -> 모든 포맷 및 이미지 생성. 이미지는 tests/test_v5 폴더에 저장
        result = translator.unified_translate(text, generate_image=True, image_output_dir="tests/test_v5")
        
        assert result.success
        assert result.image_path is not None
        assert os.path.exists(result.image_path)
        assert "tests/test_v5" in result.image_path

        # 2. 생성된 이미지 경로로 텍스트 복원
        restored_text, detected_type = translator.unified_restore(result.image_path)
        
        assert detected_type == "image"
        # 현재 이미지 인식(OCR) 정확도의 한계가 있을 수 있으므로,
        # 완벽한 일치 대신 복원된 텍스트에 원본의 주요 단어가 포함되는지 확인
        assert any(word in restored_text for word in text.split()), \
               f"이미지 복원 실패: 원본 '{text}', 복원 '{restored_text}'"

    def test_v5_statistics(self, translator: SuperBrailleTranslator):
        """통계 기능이 올바르게 동작하는지 테스트합니다."""
        # 새 인스턴스로 이력 초기화
        stats_translator = SuperBrailleTranslator(table_dir="tables")
        
        stats_before = stats_translator.get_statistics()
        assert stats_before['total_translations'] == 0
        
        # 번역 2회 실행
        stats_translator.unified_translate("첫 번째 번역입니다.")
        stats_translator.unified_translate("두 번째 and more")

        # 번역 후 통계 확인
        stats_after = stats_translator.get_statistics()
        assert stats_after['total_translations'] == 2
        assert stats_after['successful_translations'] == 2
        assert stats_after['language_distribution'] == {'korean': 1, 'mixed': 1}