import subprocess
import sys
from pathlib import Path

def convert_audio_for_azure(input_file, output_file=None):
    """
    Convert audio to Azure Speech Service compatible format:
    - 16kHz sample rate
    - Mono channel
    - 16-bit PCM WAV
    """
    input_path = Path(input_file)
    
    # Auto-generate output filename if not provided
    if output_file is None:
        output_file = input_path.stem + "_converted.wav"
    
    output_path = Path(output_file)
    
    # FFmpeg command
    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-ar', '16000',        # 16kHz sample rate
        '-ac', '1',            # Mono channel
        '-sample_fmt', 's16',  # 16-bit PCM
        '-y',                  # Overwrite output file
        str(output_path)
    ]
    
    try:
        print(f"Converting {input_path.name}...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ Successfully converted to {output_path}")
        print(f"Output: {output_path.absolute()}")
        return str(output_path)
    
    except subprocess.CalledProcessError as e:
        print(f"✗ Error converting audio: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("✗ Error: ffmpeg not found. Please install ffmpeg first.")
        sys.exit(1)

if __name__ == "__main__":
    # Usage
    input_file = "/mnt/c/Users/CraigdonLee/code/git/providend-backend-ai-api/tests/downloads/iphone_com.wav"
    output_file = convert_audio_for_azure(input_file)