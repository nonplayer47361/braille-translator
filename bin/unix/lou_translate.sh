#!/usr/bin/env bash
# macOS 홈브류 설치 경로에서 lou_translate 실행

BREW_PREFIX="$(brew --prefix)"
exec "${BREW_PREFIX}/bin/lou_translate" "$@"