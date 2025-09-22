@echo off
pushd %~dp0
if not exist backend\.venv (
  py -3 -m venv backend\.venv
)
call backend\.venv\Scripts\activate
pip install -r backend\requirements.txt
py run.py
popd
