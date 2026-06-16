from .visual import (
    GlitchEffect,
    VignettePulseEffect,
    DesaturateEffect,
    BlackAndWhiteEffect,
    FlashBangEffect,
    VHSEffect,
    MotionBlurEffect,
    DynamicGlowEffect,
    DeepfriedEffect,
)
from .temporal import SlowMotionEffect, FastForwardEffect
from .audio import BassBoostEffect, MuffleAudioEffect
from .camera import ScreenShakeEffect, ZoomPunchEffect

EFFECT_CLASSES = {
    "glitch": GlitchEffect,
    "vignette_pulse": VignettePulseEffect,
    "desaturate": DesaturateEffect,
    "black_and_white": BlackAndWhiteEffect,
    "flashbang": FlashBangEffect,
    "vhs_overlay": VHSEffect,
    "motion_blur": MotionBlurEffect,
    "dynamic_glow": DynamicGlowEffect,
    "deepfried": DeepfriedEffect,
    "slow_motion": SlowMotionEffect,
    "fast_forward": FastForwardEffect,
    "bass_boost": BassBoostEffect,
    "muffle_audio": MuffleAudioEffect,
    "screen_shake": ScreenShakeEffect,
    "zoom_punch": ZoomPunchEffect,
}


def create_effect(effect_name: str, start_time: float, duration: float):
    cls = EFFECT_CLASSES.get(effect_name)
    if cls:
        return cls(start_time, duration)
    return None


def get_capabilities_menu() -> str:
    """Dynamically generates the markdown documentation for all available effects."""
    menu = "### AVAILABLE CAPABILITIES MENU\n"
    for eff_name, cls in EFFECT_CLASSES.items():
        meta = (
            cls.get_metadata()
            if hasattr(cls, "get_metadata")
            else {
                "name": eff_name,
                "description": "No description.",
                "usage_scenario": "N/A",
            }
        )
        menu += f"- **{meta['name']}**\n"
        menu += f"  - *Description*: {meta['description']}\n"
        menu += f"  - *Usage Scenario*: {meta['usage_scenario']}\n\n"

    menu += "### AVAILABLE XFADE TRANSITIONS (for `transition_in` field)\n"
    menu += "- **fade**: Standard smooth crossfade.\n"
    menu += "- **wipeleft**: Wipes the screen from right to left.\n"
    menu += "- **slideup**: Slides the new clip up from the bottom.\n"
    menu += "- **pixelize**: Transitions by pixelating the screen heavily.\n"
    menu += "- **hblur**: Transitions by heavily blurring horizontally.\n"
    menu += "- **radial**: A circular clock-wipe transition.\n"

    return menu
