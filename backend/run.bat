@echo off
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
py run.py
