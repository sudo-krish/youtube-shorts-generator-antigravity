from .base import BaseEffect


class GlitchEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "glitch",
            "description": "Rapid RGB split flickering that creates a corrupted, digital artifact look.",
            "usage_scenario": "Use during sudden frantic movements, or right before a crazy turning point.",
        }

    def get_video_filter(self) -> str:
        enable = f"between(t,{self.start_time},{self.end_time})*lt(mod(t,0.5),0.1)"
        return f"chromashift=cbh=10:crh=-10:enable='{enable}'"


class VignettePulseEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "vignette_pulse",
            "description": "A dark shadow around the edges of the screen that pulses like a heartbeat.",
            "usage_scenario": "Use during 'Struggle' or tense holding phases where the player is waiting or hiding.",
        }

    def get_video_filter(self) -> str:
        return f"vignette='PI/4+sin(t*10)*0.2':enable='{self.enable_expr}'"


class DesaturateEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "desaturate",
            "description": "Drains the color from the screen, making it almost black and white.",
            "usage_scenario": "Use when the player takes massive damage or the situation looks hopeless.",
        }

    def get_video_filter(self) -> str:
        return f"eq=saturation=0.3:enable='{self.enable_expr}'"


class BlackAndWhiteEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "black_and_white",
            "description": "Total black and white. No color.",
            "usage_scenario": "Use for flashbacks or extreme despair.",
        }

    def get_video_filter(self) -> str:
        return f"eq=saturation=0:enable='{self.enable_expr}'"


class FlashBangEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "flashbang",
            "description": "Spikes the brightness massively, blowing out the whites.",
            "usage_scenario": "Use immediately after a massive impact or victory to signify transition.",
        }

    def get_video_filter(self) -> str:
        return f"colorlevels=rimin=0.6:gimin=0.6:bimin=0.6:enable='{self.enable_expr}'"


class VHSEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "vhs_overlay",
            "description": "Applies a retro VHS tracking distortion, slight chromatic aberration, and static noise.",
            "usage_scenario": "Use for comedic 'setup' phases or funny fails to give it a retro/meme aesthetic.",
        }

    def get_video_filter(self) -> str:
        noise = "noise=alls=20:allf=t+u"
        shift = "chromashift=cbh=2:crh=-2"
        return f"{noise},{shift}:enable='{self.enable_expr}'"


class MotionBlurEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "motion_blur",
            "description": "Simulates heavy motion blur by blending adjacent frames. Makes movement look buttery smooth but blurry.",
            "usage_scenario": "Use during fast-paced 'Speedrun' movement phases or chaotic flicks.",
        }

    def get_video_filter(self) -> str:
        return f"tblend=all_mode=average:enable='{self.enable_expr}'"


class DynamicGlowEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "dynamic_glow",
            "description": "Increases contrast and adds a soft bloom/glow to the highlights of the footage.",
            "usage_scenario": "Use for 'Mastermind' or 'Victory' moments to make the gameplay look heroic and beautiful.",
        }

    def get_video_filter(self) -> str:
        return f"eq=contrast=1.3:brightness=0.05:saturation=1.2:enable='{self.enable_expr}'"


class DeepfriedEffect(BaseEffect):
    @classmethod
    def get_metadata(cls):
        return {
            "name": "deepfried",
            "description": "Aggressive contrast, blown-out saturation, and heavy noise for an obnoxious meme look.",
            "usage_scenario": "Use for chaotic, loud meme punchlines or ridiculous fails.",
        }

    def get_video_filter(self) -> str:
        return f"eq=contrast=2.0:saturation=3.0:brightness=0.1,noise=alls=50:allf=t:enable='{self.enable_expr}'"
