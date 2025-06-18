# -*- coding: utf-8 -*-
# tests/conftest.py
import os
import sys
import logging
import pytest
from pathlib import Path

# --- 프로젝트 경로 설정 ---
# 테스트 실행 시 'braille_translator' 패키지를 찾을 수 있도록 경로를 추가합니다.
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 【수정】 __init__.py를 통해 패키지의 공식 API를 import 합니다.
# config.json 설정에 따라 v1 또는 v5의 클래스가 자동으로 할당됩니다.
from braille_translator import BrailleTranslator

# --- Pytest 공통 설정 ---

@pytest.fixture(scope="session")
def translator():
    """
    모든 테스트 세션에서 단 한 번만 생성되어 공유되는
    BrailleTranslator 인스턴스를 반환합니다.
    """
    # table_dir 인자를 전달하여 louis가 테이블 파일을 찾도록 경로를 지정합니다.
    return BrailleTranslator(table_dir="tables")

@pytest.fixture(scope="module", autouse=True)
def setup_test_directory():
    """모든 테스트 실행 전, 테스트 결과물 저장 디렉토리를 생성합니다."""
    # 테스트 결과물을 저장할 폴더를 명시적으로 생성
    (PROJECT_ROOT / "tests" / "test_v5").mkdir(exist_ok=True)