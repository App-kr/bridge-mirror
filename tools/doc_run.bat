@echo off
chcp 65001 >nul 2>&1
title BRIDGE Doc Processor

set PYTHON="D:\Phtyon 3\python.exe"
set SCRIPT="Q:\Claudework\bridge base\tools\doc_processor.py"

if "%1"=="" (
    echo.
    echo   BRIDGE Document Processor v2.1
    echo   ==============================
    echo.
    echo   doc_run setup           폴더 구조 + 상태 확인
    echo   doc_run batch           incoming/ 일괄 처리
    echo   doc_run batch --dry     미리보기만
    echo   doc_run process FILE -n 3057   단일 파일 처리
    echo   doc_run download 3057   S3 다운로드+처리
    echo   doc_run lookup NAME     후보자 검색
    echo.
    echo   incoming 폴더: Q:\Claudework\bridge base\tools\processed_docs\incoming
    echo.
    %PYTHON% -X utf8 %SCRIPT% setup
    goto :eof
)

%PYTHON% -X utf8 %SCRIPT% %*
