"""Emotion class manipulator."""
import warnings
from pathlib import Path

from ai_emotion.simple_emotion import PlutchikEmotion
from animflow import Animation

class EmotionManipulator:
    """The emotion manipulator."""
    emotion: PlutchikEmotion
    animations: list[Animation]

    def __init__(self, random: bool = False, **kwargs) -> None:
        self.get_emotion(random=random, **kwargs)
        self.get_animations()

    def get_emotion(self, random: bool = False, **kwargs):
        """Setup the initial emotion state."""
        self.emotion = PlutchikEmotion.random() if random else PlutchikEmotion(**kwargs)

    def get_animations(self):
        """Get all emotions within the `animations` folder."""
        animation_path: Path = Path(__file__).parent / "animations"

        animations: list[Animation] = []
        for file in animation_path.iterdir():
            if file.is_file() and file.suffix == ".tar.xr":
                try:
                    animation: Animation = Animation(file)
                except OSError:
                    warnings.warn(f"Unable to load animation '{file.stem}'")
                else:
                    animations.append(animation)
        self.animations = animations
