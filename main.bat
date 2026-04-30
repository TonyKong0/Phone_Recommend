@echo off
chcp 65001 >nul
cd /d "D:\汇总\temp"
call "D:\Anaconda\Scripts\activate.bat" myenv
streamlit run app.py
pause
