import os
import subprocess
import tempfile
import numpy as np
from scipy.io import wavfile
import logging

logger = logging.getLogger(__name__)


def detect_audio_spikes(video_path: str, top_n: int = 5) -> list:
    """
    Extracts the audio from a video chunk, calculates the RMS energy,
    and returns a list of float timestamps for the `top_n` loudest spikes.
    """
    logger.info(f"Generating Audio Hype Map for {os.path.basename(video_path)}...")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio_path = temp_audio.name

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            temp_audio_path,
        ]
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )

        sample_rate, data = wavfile.read(temp_audio_path)

        # Calculate RMS energy in chunks of 0.5 seconds
        chunk_size = int(sample_rate * 0.5)
        num_chunks = len(data) // chunk_size

        spike_data = []
        for i in range(num_chunks):
            chunk = data[i * chunk_size : (i + 1) * chunk_size]
            # Convert to float to avoid overflow
            chunk = chunk.astype(np.float32)
            rms = np.sqrt(np.mean(chunk**2))
            timestamp = i * 0.5
            spike_data.append((timestamp, rms))

        # Sort by loudest RMS and take top N
        spike_data.sort(key=lambda x: x[1], reverse=True)

        # Avoid clustering (if spikes are within 2 seconds of each other, ignore)
        final_spikes = []
        for ts, rms in spike_data:
            if not final_spikes:
                final_spikes.append(ts)
            else:
                if all(abs(ts - existing) > 2.0 for existing in final_spikes):
                    final_spikes.append(ts)
            if len(final_spikes) >= top_n:
                break

        return sorted(final_spikes)

    except Exception as e:
        logger.error(f"Failed to detect audio spikes: {e}")
        return []
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
