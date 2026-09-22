@echo off
set MSYSTEM=
set IDF_PATH=E:\Espressif\frameworks\esp-idf-v5.5.5
set IDF_PYTHON_ENV_PATH=E:\Espressif\python_env\idf5.5_py3.11_env
set PATH=E:\Espressif\python_env\idf5.5_py3.11_env\Scripts;E:\Espressif\tools\idf-git\2.44.0\cmd;E:\Espressif\tools\ninja\1.12.0;E:\Espressif\tools\idf-exe\1.5.3;E:\Espressif\tools\cmake\3.24.0\bin;E:\Espressif\frameworks\esp-idf-v5.5.5\tools;%PATH%
cd /d E:\FLOWIO\firmware
idf.py build
