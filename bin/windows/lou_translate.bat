@echo off
REM Windows 환경에서 PATH에 있거나 동일 디렉터리의 exe를 호출
REM 만약 lou_translate.exe를 함께 배포했다면, 아래처럼 상대경로로 실행합니다:

if exist "%~dp0lou_translate.exe" (
  "%~dp0lou_translate.exe" %*
) else (
  REM PATH에 등록된 lou_translate.exe 가 있으면 그것을 사용
  lou_translate.exe %*
)