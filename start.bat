@echo off
setlocal

:: Pythonの仮想環境が存在しない場合は作成
if not exist ".venv" (
    echo 仮想環境を作成中...
    python -m venv .venv
    call .venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

:: アプリケーションの起動
echo デスクトップエージェントを起動中...
echo 注意: 既に別のインスタンスが実行中の場合は起動できません
python src/main.py

:: エラーが発生した場合は表示
if errorlevel 1 (
    echo エラーが発生しました。
    pause
)

endlocal 