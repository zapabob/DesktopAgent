<<<<<<< HEAD
@echo off
setlocal

:: Pythonの仮想環境が存在しない場合は作成
if not exist "venv" (
    echo 仮想環境を作成中...
    python -m venv venv
    call venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: アプリケーションの起動
echo デスクトップエージェントを起動中...
python src/main.py

:: エラーが発生した場合は表示
if errorlevel 1 (
    echo エラーが発生しました。
    pause
)

=======
@echo off
setlocal

:: Pythonの仮想環境が存在しない場合は作成
if not exist "venv" (
    echo 仮想環境を作成中...
    python -m venv venv
    call venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: アプリケーションの起動
echo デスクトップエージェントを起動中...
python src/main.py

:: エラーが発生した場合は表示
if errorlevel 1 (
    echo エラーが発生しました。
    pause
)

>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
endlocal 