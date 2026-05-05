#!/usr/bin/env python3
import sys
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
            print("GUI mode requires tkinter. Install with: sudo apt install python3-tk")
            print("Falling back to CLI mode...")
            from cli import main as cli_main
            sys.argv = [sys.argv[0]] + remaining
            cli_main()

if __name__ == '__main__':
    main()
