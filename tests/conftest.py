# -*- coding: utf-8 -*-
# tests/conftest.py
import os
import sys
import logging
import pytest
from pathlib import Path

# --- 프로젝트 경로 설정 ---
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 【수정】 __init__.py를 통해 패키지의 공식 API를 import 합니다.
from braille_translator import BrailleTranslator

# --- Pytest 공통 설정 ---
@pytest.fixture(scope="session")
def translator():
    """모든 테스트에서 사용할 BrailleTranslator 인스턴스를 반환합니다."""
    return BrailleTranslator(table_dir="tables")

# ... (이하 로그 설정 및 다른 fixture는 이전과 동일) ...