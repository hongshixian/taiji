"""太极后端启动入口"""

import sys
from pathlib import Path

# 确保 backend 目录在 Python 路径上
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)