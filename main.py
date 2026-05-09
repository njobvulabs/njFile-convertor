#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description='njFile-convertor - Video and Audio File Converter')
    parser.add_argument('--cli', action='store_true', help='Run in command-line mode')
    parser.add_argument('--gui', action='store_true', help='Run in graphical mode')
    args, remaining = parser.parse_known_args()
    if args.cli or len(sys.argv) > 1 and not args.gui:
        from cli import main as cli_main
        sys.argv = [sys.argv[0]] + remaining
        cli_main()
    else:
        try:
            from gui import main as gui_main
            gui_main()
        except ImportError as e:
            if "customtkinter" in str(e):
                print("GUI mode requires customtkinter.")
            elif "tkinter" in str(e):
                print("GUI mode requires tkinter. Install with: sudo apt install python3-tk")
            else:
                print(f"GUI mode unavailable: {e}")
            print("Falling back to CLI mode...")
            from cli import main as cli_main
            sys.argv = [sys.argv[0]] + remaining
            cli_main()
        except Exception as e:
            import traceback
            msg = f"GUI mode failed: {e}\n{traceback.format_exc()}"
            print(msg, file=sys.stderr)
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
            with open(log_path, 'w') as f:
                f.write(msg + "\n")
            for cmd in [
                ["zenity", "--error", "--text", f"njFile-convertor failed to start.\n\n{e}\n\nSee {log_path} for details.", "--title", "njFile-convertor"],
                ["kdialog", "--error", f"njFile-convertor failed to start.\n\n{e}\n\nSee {log_path} for details."],
            ]:
                try:
                    subprocess.run(cmd, timeout=10)
                    break
                except Exception:
                    continue
            sys.exit(1)

if __name__ == '__main__':
    main()
