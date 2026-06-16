import os
import subprocess
import tempfile
import numpy as np
from scipy.io import wavfile


def analyze_audio_spikes(
    audio_path: str, threshold_db: float = -12.0, min_spacing_sec: float = 2.5
) -> list[float]:
    """
    Analyzes an audio/video file for amplitude spikes (screams/laughs) to trigger smart zooms.

    Args:
        audio_path: Path to the .mp4 or .wav file.
        threshold_db: The Decibel threshold above which a spike is registered.
        min_spacing_sec: Minimum seconds between punch-ins to avoid jarring zooms.

    Returns:
        List of timestamps (in seconds) where smart zooms should occur.
    """
    # 1. Extract audio to a temporary WAV file using FFmpeg
    temp_wav = tempfile.mktemp(suffix=".wav")
    try:
        # Extract mono, 44100Hz, 16-bit PCM
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            audio_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "1",
            temp_wav,
        ]
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )

        # 2. Read the WAV file
        sample_rate, data = wavfile.read(temp_wav)

        # Ensure data is 1D (mono) just in case ffmpeg downmix fails
        if len(data.shape) > 1:
            data = data[:, 0]

        # 3. Calculate windowed RMS
        window_size_sec = 0.1  # 100ms rolling window
        window_samples = int(sample_rate * window_size_sec)

        data = data.astype(np.float64)

        # Pad data so we can reshape cleanly
        pad_size = window_samples - (len(data) % window_samples)
        if pad_size != window_samples:
            data = np.pad(data, (0, pad_size), mode="constant")

        reshaped_data = data.reshape(-1, window_samples)

        # RMS = sqrt(mean(x^2))
        rms = np.sqrt(np.mean(reshaped_data**2, axis=1))

        # 4. Convert to Decibels (dBFS)
        # For 16-bit PCM, max value is 32768
        epsilon = 1e-10
        dbfs = 20 * np.log10((rms / 32768.0) + epsilon)

        # 5. Detect Spikes and apply spacing constraint
        punch_in_timestamps = []
        last_punch_in = -min_spacing_sec  # allow punch in at t=0

        for i, db in enumerate(dbfs):
            if db > threshold_db:
                current_time = i * window_size_sec
                if (current_time - last_punch_in) >= min_spacing_sec:
                    punch_in_timestamps.append(round(current_time, 2))
                    last_punch_in = current_time

        return punch_in_timestamps

    finally:
        # Cleanup
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


if __name__ == "__main__":
    # Unit test block (noop)
    pass
