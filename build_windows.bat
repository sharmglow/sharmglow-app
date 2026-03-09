@echo off
echo ============================================
echo   SmartSklad — Сборка exe
echo ============================================

echo.
echo [1/3] Установка зависимостей...
pip install -r requirements.txt

echo.
echo [2/3] Сборка exe...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name SmartSklad ^
  --add-data "ui;ui" ^
  sharmglow.py

echo.
echo [3/3] Готово!
echo Файл: dist\SmartSklad.exe
echo.
echo База данных sharmglow.db создаётся рядом с exe при первом запуске.
pause
