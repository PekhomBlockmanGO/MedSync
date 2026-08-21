import os
import sys

sys.path.append(os.getcwd())

try:
    from app.main import app
    print("FastAPI app imported successfully!")
except Exception as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)
