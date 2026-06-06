from .base import BaseEffect

class GlitchEffect(BaseEffect):
    def get_video_filter(self) -> str:
        # Rapid RGB split flickering
        enable = f"between(t,{self.start_time},{self.end_time})*lt(mod(t,0.5),0.1)"
        return f"chromashift=cbh=10:crh=-10:enable='{enable}'"

class VignettePulseEffect(BaseEffect):
    def get_video_filter(self) -> str:
        # Pulsing heartbeat vignette
        return f"vignette='PI/4+sin(t*10)*0.2':enable='{self.enable_expr}'"

class DesaturateEffect(BaseEffect):
    def get_video_filter(self) -> str:
        return f"eq=saturation=0.3:enable='{self.enable_expr}'"

class BlackAndWhiteEffect(BaseEffect):
    def get_video_filter(self) -> str:
        return f"eq=saturation=0:enable='{self.enable_expr}'"

class FlashBangEffect(BaseEffect):
    def get_video_filter(self) -> str:
        # Spikes the brightness massively
        return f"colorlevels=rimin=0.6:gimin=0.6:bimin=0.6:enable='{self.enable_expr}'"
