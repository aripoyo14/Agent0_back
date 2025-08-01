import os
import sys
import uvicorn

# 現在のディレクトリをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from app.main import app
    print("Successfully imported app.main")
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current directory: {current_dir}")
    print(f"Python path: {sys.path}")
    # 代替のインポート方法を試す
    try:
        import app.main
        app = app.main.app
        print("Successfully imported using alternative method")
    except Exception as e2:
        print(f"Alternative import also failed: {e2}")
        raise

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port) 