import os
import sys
import uvicorn

# 現在のディレクトリをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"Current working directory: {os.getcwd()}")
print(f"Current directory: {current_dir}")
print(f"Files in current directory: {os.listdir(current_dir)}")

# 複数の可能な場所をチェック
possible_paths = [
    current_dir,
    os.path.join(current_dir, 'app'),
    '/home/site/wwwroot',
    '/tmp/8ddd10a63c8f7a1',  # Azure App Serviceの一時ディレクトリ
]

for path in possible_paths:
    if os.path.exists(path):
        print(f"Path exists: {path}")
        try:
            files = os.listdir(path)
            print(f"Files in {path}: {files}")
        except Exception as e:
            print(f"Error listing files in {path}: {e}")
    else:
        print(f"Path does not exist: {path}")

try:
    from app.main import app
    print("Successfully imported app.main")
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Python path: {sys.path}")
    
    # appディレクトリが存在するかチェック
    app_dir = os.path.join(current_dir, 'app')
    if os.path.exists(app_dir):
        print(f"app directory exists: {app_dir}")
        print(f"Files in app directory: {os.listdir(app_dir)}")
    else:
        print(f"app directory does not exist: {app_dir}")
    
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