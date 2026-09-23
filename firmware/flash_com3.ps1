# flash_com3.ps1 — 直接 esptool 向 COM3 烧录（绕过 idf.py 环境检测）
$env:MSYSTEM = ''
$env:IDF_PATH = 'E:\Espressif\frameworks\esp-idf-v5.5.5'
$env:IDF_PYTHON_ENV_PATH = 'E:\Espressif\python_env\idf5.5_py3.11_env'
$env:Path = 'E:\Espressif\python_env\idf5.5_py3.11_env\Scripts;' + $env:Path
Set-Location E:\FLOWIO\firmware
& python -m esptool --chip esp32s3 -p COM3 -b 460800 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_freq 80m --flash_size 16MB 0x0 build\bootloader\bootloader.bin 0x8000 build\partition_table\partition-table.bin 0x10000 build\flowio_p0.bin
Write-Host "Exit: $LASTEXITCODE"
