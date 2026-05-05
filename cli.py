import argparse
import os
import sys
from converter import convert_file, batch_convert, VIDEO_FORMATS, AUDIO_FORMATS

def print_progress(progress):
    bar_width = 40
    filled = int(bar_width * progress / 100)
    bar = '█' * filled + '░' * (bar_width - filled)
    sys.stdout.write(f'\r[{bar}] {progress}%')
    sys.stdout.flush()
    if progress >= 100:
        print()

def main():
    parser = argparse.ArgumentParser(
        description='njFile-convertor - Convert video and audio files using ffmpeg',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Supported formats:
  Video: {', '.join(VIDEO_FORMATS)}
  Audio: {', '.join(AUDIO_FORMATS)}

Examples:
  Convert single file:
    python cli.py -i input.mp4 -o output.mkv

  Convert to audio:
    python cli.py -i video.mp4 -o audio.mp3

  Batch convert:
    python cli.py -i file1.mp4 file2.avi -o ./output --format mkv

  Show supported formats:
    python cli.py --formats
"""
    )
    parser.add_argument('-i', '--input', nargs='+', help='Input file(s)')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('-f', '--format', help='Output format (e.g., mp4, mp3, mkv)')
    parser.add_argument('--formats', action='store_true', help='Show supported formats')
    args = parser.parse_args()
    if args.formats:
        print("Supported Video Formats:")
        print("  " + ", ".join(VIDEO_FORMATS))
        print("\nSupported Audio Formats:")
        print("  " + ", ".join(AUDIO_FORMATS))
        return
    if not args.input:
        parser.print_help()
        return
    for f in args.input:
        if not os.path.exists(f):
            print(f"Error: Input file '{f}' not found")
            return
    if not args.output:
        print("Error: Output file or directory required")
        return
    if len(args.input) == 1 and not os.path.isdir(args.output):
        input_file = args.input[0]
        output_file = args.output
        if args.format:
            base = os.path.splitext(output_file)[0]
            output_file = f"{base}.{args.format}"
        print(f"Converting: {input_file} -> {output_file}")
        success, msg = convert_file(input_file, output_file, print_progress)
        if success:
            print(f"✓ {msg}")
        else:
            print(f"✗ {msg}")
    else:
        input_files = args.input
        if os.path.isdir(args.output):
            output_dir = args.output
        else:
            output_dir = args.output
            os.makedirs(output_dir, exist_ok=True)
        if not args.format:
            print("Error: --format required for batch conversion")
            return
        output_format = args.format.lstrip('.')
        print(f"Batch converting {len(input_files)} file(s) to {output_format}...")
        results = batch_convert(input_files, output_dir, output_format, print_progress)
        success_count = sum(1 for _, s, _ in results if s)
        print(f"\nCompleted: {success_count}/{len(results)} files converted successfully")
        for f, s, m in results:
            status = "✓" if s else "✗"
            print(f"  {status} {os.path.basename(f)}: {m}")

if __name__ == '__main__':
    main()
