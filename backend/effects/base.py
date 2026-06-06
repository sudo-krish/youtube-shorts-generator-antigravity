class BaseEffect:
    """Abstract base class for all dynamically applied FFmpeg effects."""
    
    def __init__(self, start_time: float, duration: float):
        self.start_time = start_time
        self.duration = duration
        self.end_time = start_time + duration if duration < 900.0 else 999.0
        
        # FFmpeg 'between' expression string for standard enable= flags
        self.enable_expr = f"between(t,{self.start_time},{self.end_time})"

    def get_video_filter(self) -> str:
        """Returns a string to be comma-appended to the video filter chain.
           e.g., "eq=saturation=0.3:enable='between(t,5,10)'"
        """
        return ""

    def get_audio_filter(self) -> str:
        """Returns a string to be comma-appended to the audio filter chain."""
        return ""
