"""Emotion class manipulator."""
import warnings
from pathlib import Path

from animflow import Animation, Displayer

class AnimationFolder:
    """Label for animation's folders."""
    EMOTIONS = "emotions"
    ACTIONS = "actions"

class EmotionManipulator:
    """The emotion manipulator."""
    displayer: Displayer
    animations: dict[str, list[Animation]]

    def __init__(
        self,
    ) -> None:
        self.setup_animation()

    def setup_animation(self):
        """Get all the animations and setup within the manipulator."""
        for folder in (AnimationFolder.EMOTIONS, AnimationFolder.ACTIONS):
            animations = self.get_animations_from_sources(folder)
            self.animations.update({
                folder: animations
            })
            for animation in animations:
                self.displayer.add_animation(animation)

    @staticmethod
    def get_animations_from_sources(folder_name: str):
        """Get all emotions within the `animations` folder."""
        animation_path: Path = Path(__file__).parent / folder_name
        if not animation_path.exists():
            return []

        animations: list[Animation] = []
        for file in animation_path.iterdir():
            if file.is_file() and file.suffix == ".tar.xr":
                try:
                    animation: Animation = Animation(file)
                except OSError:
                    warnings.warn(f"Unable to load animation '{file.stem}'")
                else:
                    animations.append(animation)
        return animations
