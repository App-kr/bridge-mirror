/*
 * silent_git.c - Native PE launcher for Q-drive git.exe
 * Calls real git.exe with CREATE_NO_WINDOW + DETACHED_PROCESS = ZERO conhost spawn
 *
 * Compile with MinGW gcc:
 *   gcc -O2 -mwindows silent_git.c -o silent_git.exe -lkernel32
 *   (or without -mwindows if console subsystem needed for stdio inheritance)
 *
 * Deploy: rename git.exe -> git_real.exe, place silent_git.exe as git.exe
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char* argv[]) {
    // 실행 경로 옆 git_real.exe 호출
    char selfPath[MAX_PATH];
    GetModuleFileNameA(NULL, selfPath, MAX_PATH);

    // selfPath 디렉토리에 git_real.exe 경로 구성
    char* slash = strrchr(selfPath, '\\');
    if (!slash) return 1;
    *(slash + 1) = '\0';
    char realGit[MAX_PATH];
    snprintf(realGit, MAX_PATH, "%sgit_real.exe", selfPath);

    // CommandLine 구성: "git_real.exe" arg1 arg2 ...
    char cmdLine[8192];
    snprintf(cmdLine, sizeof(cmdLine), "\"%s\"", realGit);
    for (int i = 1; i < argc; i++) {
        size_t cur = strlen(cmdLine);
        snprintf(cmdLine + cur, sizeof(cmdLine) - cur, " \"%s\"", argv[i]);
    }

    STARTUPINFOA si = {0};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    si.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
    si.hStdError = GetStdHandle(STD_ERROR_HANDLE);

    PROCESS_INFORMATION pi = {0};
    DWORD flags = CREATE_NO_WINDOW;

    BOOL ok = CreateProcessA(
        NULL,           // application name
        cmdLine,        // command line
        NULL, NULL,     // process / thread security
        TRUE,           // inherit handles (stdin/stdout/stderr)
        flags,
        NULL,           // env
        NULL,           // cwd
        &si, &pi
    );

    if (!ok) return GetLastError();

    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exitCode = 0;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)exitCode;
}
