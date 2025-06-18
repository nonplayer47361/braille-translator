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
    return BrailleTranslatorV2(table_dir="tables")

# --- 텍스트 ↔ 점자 기능 테스트 ---
def test_v2_initialization(translator_v2):
    assert translator_v2 is not None
    assert translator_v2.table_list == "ko-g2.ctb,en-us-g2.ctb"

def test_v2_korean_to_braille(translator_v2):
    text = "안녕하세요"
    braille = translator_v2.text_to_braille(text)
    assert isinstance(braille, str)

def test_v2_english_to_braille(translator_v2):
    text = "Hello World"
    braille = translator_v2.text_to_braille(text)
    assert isinstance(braille, str)

def test_v2_mixed_language_and_numbers_to_braille(translator_v2):
    text = "점자 번역 테스트 100%"
    braille = translator_v2.text_to_braille(text)
    assert isinstance(braille, str)

def test_v2_text_to_braille_and_back(translator_v2):
    test_cases = [
        "파이썬은 재미있는 프로그래밍 언어입니다.",
        "Braille translation using Liblouis is powerful.",
        "2025년 6월 18일, AI가 코드를 작성합니다.",
        "가격: $100, 수량: 5개 (Total: $500)"
    ]
    for text in test_cases:
        braille = translator_v2.text_to_braille(text)
        restored_text = translator_v2.braille_to_text(braille)
        assert isinstance(restored_text, str)
        assert len(restored_text.strip()) > 0

@pytest.mark.skipif(cv2 is None or np is None, reason="opencv-python 또는 numpy가 설치되지 않았습니다.")
def test_v2_text_to_braille_image(translator_v2):
    text = "테스트"
    image = translator_v2.text_to_braille_image(text)
    assert isinstance(image, np.ndarray)
    assert image.ndim == 3
    assert image.shape[2] == 3
    assert image.size > 0

@pytest.mark.skipif(cv2 is None or np is None, reason="opencv-python 또는 numpy가 설치되지 않았습니다.")
def test_v2_text_to_braille_image_generation_only(translator_v2):
    text = "점자"
    image = translator_v2.text_to_braille_image(text)
    assert isinstance(image, np.ndarray)
    assert image.ndim == 3
    assert image.shape[2] == 3
    assert image.size > 0
    os.makedirs("tests/test_data", exist_ok=True)
    image_path = os.path.join("tests/test_data", "braille_image_sample.png")
    if os.path.exists(image_path):
        os.remove(image_path)
    cv2.imwrite(image_path, image)
    print(f"[DEBUG] 샘플 점자 이미지 저장됨: {image_path}")

@pytest.mark.skipif(cv2 is None or np is None, reason="opencv-python 또는 numpy가 설치되지 않았습니다.")
def test_v2_image_to_text_round_trip(translator_v2):
    text = "이미지 왕복 테스트를 위한 예시 문장입니다. \n여러 줄로 렌더링되도록 충분히 긴 텍스트를 사용합니다."
    image = translator_v2.text_to_braille_image(text)
    print(f"[DEBUG] 생성된 이미지 크기: {image.shape}")  # (높이, 너비, 채널)
    os.makedirs("tests/test_data", exist_ok=True)
    image_path = os.path.join("tests/test_data", "round_trip_input.png")
    if os.path.exists(image_path):
        os.remove(image_path)
    cv2.imwrite(image_path, image)
    restored_text = translator_v2.image_to_text(image)
    braille = translator_v2.text_to_braille(text)
    if restored_text.strip() != text.strip():
        print(f"[DEBUG] 이미지 저장 경로: {image_path}")
        print(f"[DEBUG] 생성된 점자: '{braille}'")
        print(f"[DEBUG] 복원 결과: '{restored_text}'")
        print(f"[DEBUG] 기대 결과: '{text}'")
    assert isinstance(restored_text, str), f"결과 타입 오류: {type(restored_text)}"
    assert restored_text is not None, "복원된 텍스트가 None입니다."
    assert restored_text.strip() == text.strip(), f"복원 실패: '{restored_text}', 예상 텍스트: '{text}'"