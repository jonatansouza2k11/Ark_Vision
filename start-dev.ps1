$root="D:\Archivos\Downloads\Edx\IA\CV\OpenCV"

Start-Process powershell -WorkingDirectory $root -ArgumentList "-NoExit","-Command",".\.venv\Scripts\Activate.ps1; python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell -WorkingDirectory "$root\frontend" -ArgumentList "-NoExit","-Command","npm run dev"
