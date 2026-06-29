from .base import BaseEffect


class BassBoostEffect(BaseEffect):
    def get_audio_filter(self) -> str:
        # Boosts low frequencies massively
        return f"bass=g=15:f=110:w=0.6:enable='{self.enable_expr}'"


class MuffleAudioEffect(BaseEffect):
    def get_audio_filter(self) -> str:
        # Lowpass filter to simulate being underwater / dazed
        return f"lowpass=f=400:enable='{self.enable_expr}'"
