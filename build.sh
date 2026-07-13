#!/bin/bash
# 云原神启动器打包脚本

cd "$(dirname "$0")"

echo "=== 1. 安装 py2app ==="
pip3 install py2app

echo "=== 2. 构建 .app ==="
python3 setup.py py2app

echo "=== 3. 完成 ==="
echo ""
echo "生成的 .app 在: $(pwd)/dist/云原神启动器.app"
echo "直接双击 or open dist/云原神启动器.app 即可运行"