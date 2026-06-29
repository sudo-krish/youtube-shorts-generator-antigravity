from .base import BaseEffect


class SlowMotionEffect(BaseEffect):
    # Temporal effects are special and typically processed early in the pipeline
    def __init__(self, start_time: float, duration: float):
        super().__init__(start_time, duration)
        self.speed_factor = 1.2  # 20% slower

    def get_temporal_video_filter(self) -> str:
        # Note: This stretches the entire clip. We do not support partial slow-mo via simple string
        return f"setpts={self.speed_factor}*(PTS-STARTPTS)"

    def get_temporal_audio_filter(self) -> str:
        return f"atempo={1.0 / self.speed_factor}"


class FastForwardEffect(BaseEffect):
    def __init__(self, start_time: float, duration: float):
        super().__init__(start_time, duration)
        self.speed_factor = 0.5  # 2x faster

    def get_temporal_video_filter(self) -> str:
        return f"setpts={self.speed_factor}*(PTS-STARTPTS)"

    def get_temporal_audio_filter(self) -> str:
        return f"atempo={1.0 / self.speed_factor}"
