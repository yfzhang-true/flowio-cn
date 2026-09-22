$env:MSYSTEM = ''
$env:IDF_PATH = 'E:\Espressif\frameworks\esp-idf-v5.5.5'
$env:IDF_PYTHON_ENV_PATH = 'E:\Espressif\python_env\idf5.5_py3.11_env'
$env:Path = 'E:\Espressif\python_env\idf5.5_py3.11_env\Scripts;E:\Espressif\tools\idf-git\2.44.0\cmd;E:\Espressif\tools\ninja\1.12.0;E:\Espressif\tools\idf-exe\1.5.3;E:\Espressif\tools\cmake\3.24.0\bin;E:\Espressif\tools\xtensa-esp-elf\esp-14.2.0_20260121\xtensa-esp-elf\bin;E:\Espressif\frameworks\esp-idf-v5.5.5\tools;' + $env:Path
Set-Location E:\FLOWIO\firmware
& python E:\Espressif\frameworks\esp-idf-v5.5.5\tools\idf.py build *> E:\FLOWIO\firmware\build_output.log
Write-Host "Exit: $LASTEXITCODE"
