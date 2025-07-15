#!/usr/bin/env python3
"""
Voice typing control script
音声入力デーモンに対してシグナルを送信するスクリプト
"""

import os
import signal
import sys

PID_FILE = "/tmp/voice_typing_client.pid"


def get_daemon_pid():
    """デーモンのPIDを取得"""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            return pid
        else:
            return None
    except Exception as e:
        print(f"❌ Error reading PID: {e}")
        return None


def send_signal(signal_num):
    """デーモンにシグナルを送信"""
    pid = get_daemon_pid()
    if pid is None:
        print("❌ Daemon not running or PID file not found")
        return False

    try:
        os.kill(pid, signal_num)
        return True
    except ProcessLookupError:
        print("❌ Daemon process not found")
        # PIDファイルが古い場合は削除
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return False
    except PermissionError:
        print("❌ Permission denied to send signal")
        return False
    except Exception as e:
        print(f"❌ Error sending signal: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python voice_control.py toggle    # 録音開始/停止を切り替え")
        print("  python voice_control.py start     # 録音開始")
        print("  python voice_control.py stop      # 録音停止")
        print("  python voice_control.py status    # ステータス確認")
        print("  python voice_control.py quit      # デーモン終了")
        sys.exit(1)

    command = sys.argv[1].lower()

    # デーモンの存在確認
    pid = get_daemon_pid()
    if pid is None:
        print("❌ Daemon not running")
        sys.exit(1)

    if command in ["toggle", "start", "stop"]:
        if send_signal(signal.SIGUSR1):
            print(f"📨 Signal sent for '{command}' command")
    elif command == "status":
        if send_signal(signal.SIGUSR2):
            print("📨 Status request sent")
    elif command == "quit":
        if send_signal(signal.SIGTERM):
            print("📨 Shutdown signal sent")
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: toggle, start, stop, status, quit")


if __name__ == "__main__":
    main()
