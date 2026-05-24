"""
main.py — Entry point
Detect OS rồi gọi đúng App (WindowsApp hoặc LinuxApp).
Tương đương Program.cs trong C#.
"""

import sys
import platform


def main() -> None:
    args = sys.argv[1:]

    if platform.system() == 'Windows':
        from windows.windows_app import WindowsApp
        app = WindowsApp()
    else:
        from linux.linux_app import LinuxApp
        app = LinuxApp()

    app.run(args)


if __name__ == '__main__':
    main()
