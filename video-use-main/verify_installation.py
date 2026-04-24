#!/usr/bin/env python3
"""
验证 video-use 项目的依赖是否正确安装
"""

import sys
import subprocess

def check_python_version():
    """检查 Python 版本"""
    print("🔍 检查 Python 版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python 版本过低: {version.major}.{version.minor} (需要 >= 3.10)")
        return False

def check_python_packages():
    """检查 Python 包"""
    print("\n🔍 检查 Python 包...")
    packages = {
        'requests': 'requests',
        'librosa': 'librosa',
        'matplotlib': 'matplotlib',
        'PIL': 'pillow',
        'numpy': 'numpy',
    }
    
    all_ok = True
    for import_name, package_name in packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - 未安装")
            all_ok = False
    
    return all_ok

def check_ffmpeg():
    """检查 ffmpeg 和 ffprobe"""
    print("\n🔍 检查 ffmpeg...")
    
    all_ok = True
    for cmd in ['ffmpeg', 'ffprobe']:
        try:
            result = subprocess.run(
                [cmd, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✅ {cmd}: {version_line}")
            else:
                print(f"❌ {cmd}: 命令执行失败")
                all_ok = False
        except FileNotFoundError:
            print(f"❌ {cmd}: 未找到命令")
            all_ok = False
        except Exception as e:
            print(f"❌ {cmd}: {str(e)}")
            all_ok = False
    
    return all_ok

def check_env_file():
    """检查 .env 文件"""
    print("\n🔍 检查 .env 文件...")
    try:
        with open('.env', 'r') as f:
            content = f.read()
            if 'ELEVENLABS_API_KEY=' in content:
                # 检查是否有实际的 key（不是空的）
                for line in content.split('\n'):
                    if line.startswith('ELEVENLABS_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        if key:
                            print(f"✅ .env 文件存在，API Key 已配置")
                            return True
                        else:
                            print(f"⚠️  .env 文件存在，但 API Key 未配置")
                            print("   请在 .env 文件中填入您的 ELEVENLABS_API_KEY")
                            return False
        print("❌ .env 文件格式不正确")
        return False
    except FileNotFoundError:
        print("❌ .env 文件不存在")
        print("   请运行: cp .env.example .env")
        return False

def check_helper_scripts():
    """检查 helper 脚本"""
    print("\n🔍 检查 helper 脚本...")
    import os
    
    helpers = [
        'helpers/transcribe.py',
        'helpers/transcribe_batch.py',
        'helpers/pack_transcripts.py',
        'helpers/timeline_view.py',
        'helpers/render.py',
        'helpers/grade.py',
    ]
    
    all_ok = True
    for helper in helpers:
        if os.path.exists(helper):
            print(f"✅ {helper}")
        else:
            print(f"❌ {helper} - 文件不存在")
            all_ok = False
    
    return all_ok

def main():
    print("=" * 60)
    print("video-use 依赖验证")
    print("=" * 60)
    
    checks = [
        ("Python 版本", check_python_version),
        ("Python 包", check_python_packages),
        ("ffmpeg", check_ffmpeg),
        (".env 文件", check_env_file),
        ("Helper 脚本", check_helper_scripts),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 检查 {name} 时出错: {str(e)}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 所有依赖检查通过！项目已就绪。")
        print("\n下一步:")
        print("1. 在 .env 文件中配置您的 ELEVENLABS_API_KEY")
        print("2. 准备视频素材")
        print("3. 使用 Claude Code 或手动运行 helper 脚本")
    else:
        print("⚠️  部分依赖检查失败。请查看上方的详细信息并修复。")
        print("\n常见问题:")
        print("- ffmpeg 未找到: 重启终端或运行 'winget install Gyan.FFmpeg'")
        print("- Python 包缺失: 运行 'pip install -e .'")
        print("- .env 文件: 复制 .env.example 并填入 API Key")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
