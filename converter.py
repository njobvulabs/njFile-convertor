import subprocess
import os
import re
import json
import threading

# Global pause event for controlling conversion flow
pause_event = threading.Event()
pause_event.set()  # Set initially (not paused)

# Stop event for cancelling conversions
stop_event = threading.Event()

def pause_conversion():
    """Pause the conversion queue"""
    pause_event.clear()

def resume_conversion():
    """Resume the conversion queue"""
    pause_event.set()

def is_paused():
    """Check if conversion is paused"""
    return not pause_event.is_set()

def stop_conversion():
    """Signal to stop conversions"""
    stop_event.set()

def reset_stop():
    """Reset the stop signal"""
    stop_event.clear()

VIDEO_FORMATS = ['mp4', 'avi', 'mkv', 'mov', 'webm', 'flv', 'wmv', 'm4v', '3gp', 'mpg', 'mpeg']
AUDIO_FORMATS = ['mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a', 'wma']

QUALITY_PRESETS = {
    'low': {'video_bitrate': '500k', 'audio_bitrate': '64k', 'crf': '35'},
    'medium': {'video_bitrate': '1500k', 'audio_bitrate': '128k', 'crf': '23'},
    'high': {'video_bitrate': '4000k', 'audio_bitrate': '192k', 'crf': '18'},
    'ultra': {'video_bitrate': '8000k', 'audio_bitrate': '320k', 'crf': '15'}
}

RESOLUTION_MAP = {
    'original': None,
    '480p': '640:480',
    '720p': '1280:720',
    '1080p': '1920:1080',
    '4K': '3840:2160'
}

def get_video_codec(output_format):
    codecs = {
        'mp4': ['-c:v', 'libx264', '-c:a', 'aac'],
        'avi': ['-c:v', 'mpeg4', '-c:a', 'mp3'],
        'mkv': ['-c:v', 'libx264', '-c:a', 'aac'],
        'mov': ['-c:v', 'libx264', '-c:a', 'aac'],
        'webm': ['-c:v', 'libvpx', '-c:a', 'libvorbis'],
        'flv': ['-c:v', 'flv', '-c:a', 'mp3'],
        'wmv': ['-c:v', 'wmv2', '-c:a', 'wmav2'],
        'm4v': ['-c:v', 'libx264', '-c:a', 'aac'],
        '3gp': ['-c:v', 'libx264', '-c:a', 'aac'],
        'mpg': ['-c:v', 'mpeg2video', '-c:a', 'mp2'],
        'mpeg': ['-c:v', 'mpeg2video', '-c:a', 'mp2']
    }
    return codecs.get(output_format, ['-c:v', 'libx264', '-c:a', 'aac'])

def get_audio_codec(output_format):
    codecs = {
        'mp3': ['-c:a', 'libmp3lame'],
        'wav': ['-c:a', 'pcm_s16le'],
        'aac': ['-c:a', 'aac'],
        'flac': ['-c:a', 'flac'],
        'ogg': ['-c:a', 'libvorbis'],
        'm4a': ['-c:a', 'aac'],
        'wma': ['-c:a', 'wmav2']
    }
    return codecs.get(output_format, ['-c:a', 'libmp3lame'])

def get_ffmpeg_params(settings=None):
    """Build ffmpeg parameters based on settings dict"""
    if settings is None:
        settings = {}
    params = []
    quality = settings.get('quality', 'medium')
    if quality in QUALITY_PRESETS:
        preset = QUALITY_PRESETS[quality]
        params.extend(['-b:v', preset['video_bitrate']])
        params.extend(['-b:a', preset['audio_bitrate']])
        params.extend(['-crf', preset['crf']])
    resolution = settings.get('resolution', 'original')
    if resolution in RESOLUTION_MAP and RESOLUTION_MAP[resolution]:
        params.extend(['-vf', f"scale={RESOLUTION_MAP[resolution]}"])
    if settings.get('audio_channels'):
        params.extend(['-ac', str(settings['audio_channels'])])
    if settings.get('sample_rate'):
        params.extend(['-ar', str(settings['sample_rate'])])
    if settings.get('frame_rate'):
        params.extend(['-r', str(settings['frame_rate'])])
    if settings.get('custom_params'):
        params.extend(settings['custom_params'].split())
    return params

def get_media_type(file_path):
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    if ext in VIDEO_FORMATS:
        return 'video'
    elif ext in AUDIO_FORMATS:
        return 'audio'
    return None

def get_file_info(file_path):
    """Get file metadata using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            info = {'file_path': file_path, 'format': 'Unknown', 'duration': 0,
                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'video': None, 'audio': None}
            if 'format' in data:
                fmt = data['format']
                info['format'] = fmt.get('format_name', 'Unknown').split(',')[0]
                info['duration'] = float(fmt.get('duration', 0))
                info['bitrate'] = int(fmt.get('bit_rate', 0))
            for stream in data.get('streams', []):
                codec_type = stream.get('codec_type')
                if codec_type == 'video' and not info['video']:
                    info['video'] = {
                        'codec': stream.get('codec_name', 'Unknown'),
                        'width': stream.get('width'),
                        'height': stream.get('height'),
                        'fps': eval(stream.get('r_frame_rate', '0/1')) if '/' in stream.get('r_frame_rate', '') else 0
                    }
                elif codec_type == 'audio' and not info['audio']:
                    info['audio'] = {
                        'codec': stream.get('codec_name', 'Unknown'),
                        'sample_rate': int(stream.get('sample_rate', 0)),
                        'channels': stream.get('channels', 0)
                    }
            return info
    except:
        pass
    return None

def run_ffmpeg(cmd, progress_callback=None):
    try:
        duration = get_duration(cmd[2]) if len(cmd) > 2 else 0
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        stderr_output = []
        while True:
            # Check for pause
            if not pause_event.is_set():
                process.send_signal(subprocess.signal.SIGSTOP)
                pause_event.wait()  # Wait until resumed
                process.send_signal(subprocess.signal.SIGCONT)

            # Check for stop
            if stop_event.is_set():
                process.terminate()
                return False, "Conversion stopped by user"

            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if line:
                stderr_output.append(line)
                if progress_callback and 'time=' in line:
                    time_match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
                    if time_match:
                        current_time = parse_time(time_match.group(1))
                        if duration > 0:
                            progress = min(100, int((current_time / duration) * 100))
                            progress_callback(progress)

        return_code = process.wait()
        if return_code == 0:
            if progress_callback:
                progress_callback(100)
            return True, "Conversion completed successfully"
        else:
            error_msg = ''.join(stderr_output[-10:]) if stderr_output else "Unknown error"
            return False, f"FFmpeg error: {error_msg}"
    except FileNotFoundError:
        return False, "ffmpeg not found. Please install ffmpeg."
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_duration(input_file):
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
               '-of', 'default=noprint_wrappers=1:nokey=1', input_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration_match = re.search(r'(\d+\.\d+)', result.stdout)
        if duration_match:
            return float(duration_match.group(1))
    except:
        pass
    return 0

def parse_time(time_str):
    try:
        parts = time_str.split(':')
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0

def convert_video_to_video(input_file, output_file, progress_callback=None, settings=None):
    output_format = os.path.splitext(output_file)[1].lower().lstrip('.')
    cmd = ['ffmpeg', '-i', input_file, '-y']
    cmd.extend(get_video_codec(output_format))
    cmd.extend(get_ffmpeg_params(settings))
    cmd.append(output_file)
    return run_ffmpeg(cmd, progress_callback)

def convert_audio_to_audio(input_file, output_file, progress_callback=None, settings=None):
    output_format = os.path.splitext(output_file)[1].lower().lstrip('.')
    cmd = ['ffmpeg', '-i', input_file, '-y']
    cmd.extend(get_audio_codec(output_format))
    cmd.extend(get_ffmpeg_params(settings))
    cmd.append(output_file)
    return run_ffmpeg(cmd, progress_callback)

def convert_video_to_audio(input_file, output_file, progress_callback=None, settings=None):
    output_format = os.path.splitext(output_file)[1].lower().lstrip('.')
    cmd = ['ffmpeg', '-i', input_file, '-vn', '-y']
    cmd.extend(get_audio_codec(output_format))
    cmd.extend(get_ffmpeg_params(settings))
    cmd.append(output_file)
    return run_ffmpeg(cmd, progress_callback)

def convert_file(input_file, output_file, progress_callback=None, settings=None):
    input_type = get_media_type(input_file)
    output_ext = os.path.splitext(output_file)[1].lower().lstrip('.')
    if not input_type:
        return False, "Unsupported input format"
    if output_ext not in VIDEO_FORMATS and output_ext not in AUDIO_FORMATS:
        return False, "Unsupported output format"
    if input_type == 'video' and output_ext in VIDEO_FORMATS:
        return convert_video_to_video(input_file, output_file, progress_callback, settings)
    elif input_type == 'audio' and output_ext in AUDIO_FORMATS:
        return convert_audio_to_audio(input_file, output_file, progress_callback, settings)
    elif input_type == 'video' and output_ext in AUDIO_FORMATS:
        return convert_video_to_audio(input_file, output_file, progress_callback, settings)
    else:
        return False, f"Cannot convert {input_type} to {output_ext}"

def batch_convert(input_files, output_dir, output_format, progress_callback=None, settings=None):
    results = []
    total = len(input_files)
    for i, input_file in enumerate(input_files):
        if stop_event.is_set():
            results.append((input_file, None, False, "Stopped"))
            break
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        if settings and settings.get('naming_pattern'):
            pattern = settings['naming_pattern']
            output_file = os.path.join(output_dir, f"{pattern.replace('{name}', base_name)}.{output_format}")
        else:
            output_file = os.path.join(output_dir, f"{base_name}.{output_format}")
        def file_progress(p):
            if progress_callback:
                overall = int(((i + p/100) / total) * 100)
                progress_callback(overall)
        success, msg = convert_file(input_file, output_file, file_progress, settings)
        results.append((input_file, output_file, success, msg))
    return results

def watch_folder(input_dir, output_dir, output_format, settings=None, callback=None, stop_check=None):
    """
    Watch a folder and auto-convert new media files
    stop_check: function that returns True when watching should stop
    callback: function to call with (input_file, output_file, success, msg)
    """
    processed = set()
    # Load previously processed files
    history_file = os.path.join(output_dir, '.watch_history.json')
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                processed = set(json.load(f))
        except:
            processed = set()

    while True:
        if stop_check and stop_check():
            break
        try:
            with os.scandir(input_dir) as entries:
                for entry in entries:
                    if entry.is_file() and not entry.name.startswith('.'):
                        ext = os.path.splitext(entry.name)[1].lower().lstrip('.')
                        if ext in VIDEO_FORMATS or ext in AUDIO_FORMATS:
                            if entry.path not in processed:
                                # Convert the file
                                output_file = os.path.join(
                                    output_dir,
                                    f"{os.path.splitext(entry.name)[0]}.{output_format}"
                                )
                                if callback:
                                    callback(entry.path, output_file, "Converting")
                                success, msg = convert_file(entry.path, output_file, settings=settings)
                                processed.add(entry.path)
                                if callback:
                                    status = "Done" if success else "Error"
                                    callback(entry.path, output_file, status)
                                # Save history
                                with open(history_file, 'w') as f:
                                    json.dump(list(processed), f)
        except Exception as e:
            if callback:
                callback(None, None, f"Error: {str(e)}")
        # Wait before next scan
        import time
        for _ in range(20):  # Check stop every 0.5s for 10s total
            if stop_check and stop_check():
                return
            time.sleep(0.5)
