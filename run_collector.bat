@echo off
chcp 65001 > nul
setlocal

:: 중요: pushd를 하기 전, 현재 CMD가 떠 있는 위치를 변수에 저장합니다.
set "CURRENT_CMD_DIR=%cd%"

:: 이제 스크립트 실행을 위해 배치파일 폴더로 이동합니다.
pushd "%~dp0"

set PY_FILE=origin\collect_markdown_assets.py

echo [파일 탐색기를 실행합니다...]
:: 파이썬에 CMD 위치(%CURRENT_CMD_DIR%)를 인자로 넘깁니다.
python "%PY_FILE%" "%CURRENT_CMD_DIR%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [알림] 작업이 취소되었거나 문제가 발생했습니다.
    pause
) else (
    echo.
    echo [성공] 모든 작업이 완료되었습니다.
    timeout /t 3
)

popd