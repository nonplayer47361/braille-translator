# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
import importlib

# 패키지 버전
__version__ = "0.6.0"

# --- 설정 파일 로드 및 동적 Import ---
try:
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    ACTIVE_VERSION = config.get("active_translator_version", "v5") # 기본값 v5
    version_info = config["versions"][ACTIVE_VERSION]

    module_name = f".{version_info['module']}"
    class_name = version_info['class']
    
    translator_module = importlib.import_module(module_name, package=__name__)
    BrailleTranslator = getattr(translator_module, class_name)

except (FileNotFoundError, KeyError, ImportError) as e:
    raise ImportError(
        f"활성 버전 '{ACTIVE_VERSION}'을 불러오는 데 실패했습니다. "
        f"config.json 설정이나 모듈 파일('{version_info.get('module')}.py')이 올바른지 확인해주세요. 오류: {e}"
    )

# --- 공개 API 설정 ---
__all__ = [
    "BrailleTranslator",  # 현재 활성화된 버전의 번역기 클래스
]

# V5 버전이 활성화된 경우에만 V5 전용 클래스들을 공개합니다.
if ACTIVE_VERSION == 'v5':
    try:
        from .translator_v5 import (
            InputFormatDetector,
            LanguageDetector,
            LanguageType,
            ContractionLevel,
            UnifiedTranslationResult,
            HAS_IMAGE_SUPPORT
        )
        __all__.extend([
            "InputFormatDetector",
            "LanguageDetector",
            "LanguageType",
            "ContractionLevel",
            "UnifiedTranslationResult",
            "HAS_IMAGE_SUPPORT"
        ])
    except ImportError:
        # translator_v5 파일이나 내부 클래스가 없을 경우를 대비
        pass