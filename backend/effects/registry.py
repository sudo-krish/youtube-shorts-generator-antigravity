from .visual import GlitchEffect, VignettePulseEffect, DesaturateEffect, BlackAndWhiteEffect, FlashBangEffect
from .temporal import SlowMotionEffect, FastForwardEffect
from .audio import BassBoostEffect, MuffleAudioEffect
from .camera import ScreenShakeEffect, ZoomPunchEffect

EFFECT_CLASSES = {
    "glitch": GlitchEffect,
    "vignette_pulse": VignettePulseEffect,
    "desaturate": DesaturateEffect,
    "black_and_white": BlackAndWhiteEffect,
    "flashbang": FlashBangEffect,
    "slow_motion": SlowMotionEffect,
    "fast_forward": FastForwardEffect,
    "bass_boost": BassBoostEffect,
    "muffle_audio": MuffleAudioEffect,
    "screen_shake": ScreenShakeEffect,
    "zoom_punch": ZoomPunchEffect
}

def create_effect(effect_name: str, start_time: float, duration: float):
    cls = EFFECT_CLASSES.get(effect_name)
    if cls:
        return cls(start_time, duration)
    return None
