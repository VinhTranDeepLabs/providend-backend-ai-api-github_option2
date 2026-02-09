import io
import numpy as np
import soundfile as sf
from scipy import signal
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def convert_webm_to_wav_mono_48k(webm_bytes: bytes) -> Tuple[bytes, str]:
    """
    Convert WebM audio to WAV format (mono, 48kHz, 16-bit PCM)
    
    Args:
        webm_bytes: Input WebM audio file as bytes
    
    Returns:
        Tuple of (wav_bytes, error_message)
        - wav_bytes: Converted WAV file as bytes (None if error)
        - error_message: Error description (None if success)
    """
    try:
        # Read WebM audio data
        audio_data, sample_rate = sf.read(io.BytesIO(webm_bytes))
        
        logger.info(f"Original audio - Sample rate: {sample_rate}Hz, Shape: {audio_data.shape}")
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            # Average all channels to mono
            audio_data = np.mean(audio_data, axis=1)
            logger.info("Converted stereo to mono")
        
        # Resample to 48kHz if needed
        target_sample_rate = 48000
        if sample_rate != target_sample_rate:
            # Calculate the number of samples in the resampled audio
            num_samples = int(len(audio_data) * target_sample_rate / sample_rate)
            audio_data = signal.resample(audio_data, num_samples)
            sample_rate = target_sample_rate
            logger.info(f"Resampled to {target_sample_rate}Hz")
        
        # Ensure audio is in the correct range for 16-bit PCM (-1.0 to 1.0)
        audio_data = np.clip(audio_data, -1.0, 1.0)
        
        # Write to WAV format in memory
        wav_buffer = io.BytesIO()
        sf.write(
            wav_buffer,
            audio_data,
            samplerate=sample_rate,
            subtype='PCM_16',  # 16-bit PCM
            format='WAV'
        )
        
        # Get bytes
        wav_buffer.seek(0)
        wav_bytes = wav_buffer.read()
        
        logger.info(f"Conversion successful - Output size: {len(wav_bytes)} bytes")
        
        return wav_bytes, None
        
    except Exception as e:
        error_msg = f"Audio conversion failed: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def validate_audio_file(file_bytes: bytes, max_size_mb: int = 200) -> Tuple[bool, str]:
    """
    Validate audio file size and format
    
    Args:
        file_bytes: Audio file as bytes
        max_size_mb: Maximum file size in MB
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        return False, f"File too large ({file_size_mb:.2f}MB). Maximum size: {max_size_mb}MB"
    
    # Try to read audio metadata
    try:
        sf.read(io.BytesIO(file_bytes))
        return True, None
    except Exception as e:
        return False, f"Invalid audio file: {str(e)}"