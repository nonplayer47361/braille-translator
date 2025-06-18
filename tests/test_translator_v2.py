# -*- coding: utf-8 -*-
import pytest
import os

try:
    import numpy as np
    import cv2
except ImportError:
    np = None
    cv2 = None

from braille_translator.translator_v2 import BrailleTranslatorV2

@pytest.fixture(scope="module")
def translator_v2():
    """테스트 전체에서 사용할 BrailleTranslatorV2 인스턴스를 생성합니다."""
    return BrailleTranslatorV2(table_dir="tables", table_list="ko-g2.ctb,en-us-g2.ctb")

# --- 텍스트 ↔ 점자 기능 테스트 ---
def test_v2_initialization(translator_v2):
    """V2 번역기 클래스가 정상적으로 초기화되는지 확인합니다."""
    assert translator_v2 is not None
    assert translator_v2.table_list == "ko-g2.ctb,en-us-g2.ctb"

def test_v2_korean_to_braille(translator_v2):
    """한글 텍스트 -> 점자 변환을 테스트합니다."""
    text = "안녕하세요"
    braille = translator_v2.text_to_braille(text)
    expected_braille = "⠁⠝⠒⠠⠕⠢⠠⠚⠒⠂⠁⠎⠢⠠⠚"
    assert braille == expected_braille

def test_v2_english_to_braille(translator_v2):
    """영문 텍스트 -> 점자 변환을 테스트합니다."""
    text = "Hello World"
    braille = translator_v2.text_to_braille(text)
    expected_braille = "⠠⠓⠑⠇⠇⠕ ⠠⠺⠕⠗⠇⠙"
    assert braille == expected_braille

def test_v2_mixed_language_and_numbers_to_braille(translator_v2):
    """한영, 숫자, 기호가 혼합된 텍스트의 변환을 테스트합니다."""
    text = "점자 번역 테스트 100%"
    braille = translator_v2.text_to_braille(text)
    expected_braille = "⠚⠢⠍⠘⠁ ⠃⠥⠒⠠⠡ ⠞⠢⠎⠞ ⠼⠁⠚⠚⠴"
    assert braille == expected_braille

def test_v2_text_to_braille_and_back(translator_v2):
    """텍스트-점자 왕복 변환이 정확한지 테스트합니다."""
    test_cases = [
        "파이썬은 재미있는 프로그래밍 언어입니다.",
        "Braille translation using Liblouis is powerful.",
        "2025년 6월 18일, AI가 코드를 작성합니다.",
        "가격: $100, 수량: 5개 (Total: $500)"
    ]
    for text in test_cases:
        braille = translator_v2.text_to_braille(text)
        restored_text = translator_v2.braille_to_text(braille)
        assert text == restored_text, f"왕복 변환 실패: '{text}' -> '{braille}' -> '{restored_text}'"

# --- 이미지 관련 기능 테스트 ---
@pytest.mark.skipif(cv2 is None or np is None, reason="opencv-python 또는 numpy가 설치되지 않았습니다.")
def test_v2_text_to_braille_image(translator_v2):
    """텍스트를 점자 이미지로 변환하는 기능을 테스트합니다."""
    text = "테스트"
    image = translator_v2.text_to_braille_image(text)
    assert isinstance(image, np.ndarray)
    assert image.ndim == 3
    assert image.shape[2] == 3
    assert image.size > 0

@pytest.mark.skipif(cv2 is None or np is None, reason="opencv-python 또는 numpy가 설치되지 않았습니다.")
def test_v2_image_to_text_round_trip(translator_v2):
    """이미지 변환 왕복 테스트. 생성과 복원 시 동일한 파라미터를 사용합니다."""
    text = "이미지 왕복 테스트"
    
    # 이미지 생성/복원에 사용할 동일한 파라미터 정의
    dot_radius = 6
    cell_size = 40
    margin = 20
    threshold = 128
    
    # 정의된 파라미터로 이미지 생성
    image = translator_v2.text_to_braille_image(
        text, dot_radius=dot_radius, cell_size=cell_size, margin=margin
    )
    
    # 생성과 동일한 파라미터로 복원 수행
    restored_text = translator_v2.image_to_text(
        image, cell_size=cell_size, margin=margin, threshold=threshold, dot_radius=dot_radius
    )
    
    # 완벽한 텍스트 복원을 검증
    assert text == restored_text, f"이미지 왕복 변환 실패: '{text}' -> (이미지) -> '{restored_text}'"