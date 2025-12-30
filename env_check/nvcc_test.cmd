@echo off
call "D:\VisualStudio\2022Community\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_PATH=D:\softwares\cuda"
set "PATH=%CUDA_PATH%\bin;%CUDA_PATH%\libnvvp;%PATH%"
REM Force local temp to avoid path/ACL issues
set "_LOCAL_TMP=E:\projects\AiforForiegnLanguageLearning\env_check\tmp"
if not exist "%_LOCAL_TMP%" mkdir "%_LOCAL_TMP%"
set "TMP=%_LOCAL_TMP%"
set "TEMP=%_LOCAL_TMP%"
echo ===== NVCC TOOLCHAIN SANITY CHECK ===== > E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo DATE: %DATE% %TIME% >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo CUDA_PATH=%CUDA_PATH% >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo VCToolsInstallDir=%VCToolsInstallDir% >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo VisualStudioVersion=%VisualStudioVersion% >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo WindowsSdkDir=%WindowsSdkDir% >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo WindowsSDKVersion=%WindowsSDKVersion% >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo --------------------------------------- >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log

echo where nvcc >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
where nvcc >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1
echo nvcc --version >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
"%CUDA_PATH%\bin\nvcc.exe" --version >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1

echo where cl >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
where cl >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1
echo cl /Bv >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
cl /Bv >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1

set "CCBIN_EXE=%VCToolsInstallDir%bin\Hostx64\x64\cl.exe"
echo Using -ccbin "%CCBIN_EXE%" >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log

echo --- NVCC COMPILE (obj, sm_120) --- >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo (dryrun) "%CUDA_PATH%\bin\nvcc.exe" --dryrun -v -ccbin="%CCBIN_EXE%" -arch=sm_120 -c E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test.obj >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
"%CUDA_PATH%\bin\nvcc.exe" --dryrun -v -ccbin="%CCBIN_EXE%" -arch=sm_120 -c E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test.obj >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1
echo "%CUDA_PATH%\bin\nvcc.exe" -v -ccbin="%CCBIN_EXE%" -arch=sm_120 -Xcompiler="/Zm2000 /EHsc /MD" -c E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test.obj >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
"%CUDA_PATH%\bin\nvcc.exe" -v -ccbin="%CCBIN_EXE%" -arch=sm_120 -Xcompiler="/Zm2000 /EHsc /MD" -c E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test.obj >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1
if errorlevel 1 goto :fail
echo --- NVCC LINK (exe, sm_120) --- >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo "%CUDA_PATH%\bin\nvcc.exe" -v -ccbin="%CCBIN_EXE%" -arch=sm_120 E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test.exe >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
"%CUDA_PATH%\bin\nvcc.exe" -v -ccbin="%CCBIN_EXE%" -arch=sm_120 E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test.exe >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1
if errorlevel 1 goto :fail
echo --- NVCC COMPILE (obj, sm_89) --- >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo "%CUDA_PATH%\bin\nvcc.exe" -v -ccbin="%CCBIN_EXE%" -arch=sm_89 -c E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test_sm89.obj >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
"%CUDA_PATH%\bin\nvcc.exe" -v -ccbin="%CCBIN_EXE%" -arch=sm_89 -c E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test_sm89.obj >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1
if errorlevel 1 goto :fail

echo --- NVCC LINK (exe, sm_89) --- >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
echo "%CUDA_PATH%\bin\nvcc.exe" -v -ccbin="%CCBIN_EXE%" -arch=sm_89 E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test_sm89.exe >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
"%CUDA_PATH%\bin\nvcc.exe" -v -ccbin="%CCBIN_EXE%" -arch=sm_89 E:\projects\AiforForiegnLanguageLearning\env_check\test.cu -o E:\projects\AiforForiegnLanguageLearning\env_check\test_sm89.exe >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log 2>&1
if errorlevel 1 goto :fail

echo NVCC_OK >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
exit /b 0

:fail
echo NVCC_FAIL >> E:\projects\AiforForiegnLanguageLearning\env_check\test_nvcc.log
exit /b 1
