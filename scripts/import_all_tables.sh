#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# 1) 스크립트가 실행되는 디렉터리(프로젝트 루트)로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  

# 2) 소스/대상 디렉터리 설정 (절대 경로)
SRC_DIR="liblouis-src/tables"
DEST_DIR="tables"

# 3) 소스가 존재하는지 확인
if [[ ! -d "$SRC_DIR" ]]; then
  echo "❌ 소스 테이블 디렉터리가 없습니다: $SRC_DIR" >&2
  exit 1
fi

# 4) 이전 테이블 백업(선택 사항)
if [[ -d "$DEST_DIR" ]]; then
  mv "$DEST_DIR" "${DEST_DIR}-backup-$(date +%Y%m%d-%H%M%S)"
  echo "🔄 이전 $DEST_DIR 를 백업했습니다."
fi

# 5) 전체 복사 (보존 모드)
mkdir -p "$DEST_DIR"
cp -a "$SRC_DIR/." "$DEST_DIR/"
echo "✅ 프로젝트 내부에 liblouis 모든 테이블을 복사했습니다: $DEST_DIR/"

# 6) display‐table 확인: unicode.dis
DISPLAY_TABLE="$DEST_DIR/unicode.dis"
if [[ ! -f "$DISPLAY_TABLE" ]]; then
  echo "❌ display table 'unicode.dis'를 찾을 수 없습니다: $DISPLAY_TABLE" >&2
  exit 1
else
  echo "✅ display table 'unicode.dis' 확인됨."
fi