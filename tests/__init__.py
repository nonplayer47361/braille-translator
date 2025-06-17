# File: tests/__init__.py
# Purpose: tests 패키지 초기화 및 공통 설정

"""
tests 패키지
-------------
이 디렉터리 아래에 있는 모든 테스트 모듈이 공유하는
설정이나 fixture를 정의합니다.

- 프로젝트 루트를 PYTHONPATH에 추가하여
  braille_translator 모듈을 바로 가져올 수 있게 합니다.
- pytest용 설정이나 전역 fixture를 이곳에 정의할 수 있습니다.
"""

import os
import sys

# 프로젝트 루트 디렉터리 (tests/ 의 상위 폴더)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# braille_translator 패키지가 import 가능하도록 경로 설정
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 필요하다면 전역 pytest fixture를 여기에 정의할 수 있습니다.
# 예를 들어:
#
# import pytest
#
# @pytest.fixture(scope="session")
# def sample_texts():
#     return {
#         "english": ["and", "hello", "the", "zigzag"],
#         "korean": ["안녕", "한글", "감사합니다"],
#         "mixed": ["Hello 안녕 123!", "Test 테스트, 42번!"],
#     }
#
# 그런 다음 각 테스트에서 sample_texts fixture를 사용할 수 있습니다.