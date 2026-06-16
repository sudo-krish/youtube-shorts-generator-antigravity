from .base import BaseEffect


class ScreenShakeEffect(BaseEffect):
    # This effect needs to interface with the crop filter logic
    def get_crop_offset(self) -> str:
        # Adds horizontal shake
        return f"if({self.enable_expr},sin(t*40)*20,0)"


class ZoomPunchEffect(BaseEffect):
    # This is a global zoompan effect that editor.py will collect
    pass
