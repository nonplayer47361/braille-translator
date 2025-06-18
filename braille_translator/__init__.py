# -*- coding: utf-8 -*-
"""
braille-translator 패키지
V5 엔진을 기본으로 공개합니다.
"""
__version__ = "0.5.0"

# 【수정】 translator_v5 모듈에서 이름이 변경된 클래스들을 가져옵니다.
from .translator_v5 import (
    BrailleTranslator,
    InputFormatDetector,
    LanguageDetector,
    LanguageType,
    ContractionLevel,
    UnifiedTranslationResult,
    HAS_IMAGE_SUPPORT
)

# 【수정】 공개 API 목록에서 클래스 이름을 변경합니다.
__all__ = [
    "BrailleTranslator",
    "InputFormatDetector",
    "LanguageDetector",
    "LanguageType",
    "ContractionLevel",
    "UnifiedTranslationResult",
    "HAS_IMAGE_SUPPORT"
]