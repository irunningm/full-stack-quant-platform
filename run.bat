@echo off
set PYTHONUTF8=1
% uv run streamlit run app.py
uv run python -X utf8 streamlit run app.py