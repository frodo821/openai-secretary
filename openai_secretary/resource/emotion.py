from dataclasses import dataclass
from random import random
from typing import TypeAlias

floats5: TypeAlias = tuple[float, float, float, float, float]


@dataclass
class Emotion:
  _anger: float
  _disgust: float
  _fear: float
  _joy: float
  _sadness: float

  @classmethod
  def random_emotion(cls, *, weights: floats5 = (0.1, 0.1, 0.1, 0.6, 0.1)):
    return cls(
      _anger=min(random() * weights[0], 1.0),
      _disgust=min(random() * weights[1], 1.0),
      _fear=min(random() * weights[2], 1.0),
      _joy=min(random() * weights[3], 1.0),
      _sadness=min(random() * weights[4], 1.0),
    )

  @property
  def magnitude(self) -> float:
    return (self.anger**2 + self.disgust**2 + self.fear**2 + self.joy**2 + self.sadness**2)**0.5

  @property
  def normalized(self) -> 'Emotion':
    return self / self.magnitude

  @property
  def anger(self) -> float:
    return self._anger

  @anger.setter
  def anger(self, value: float):
    self._anger = value

  @property
  def disgust(self) -> float:
    return self._disgust

  @disgust.setter
  def disgust(self, value: float):
    self._disgust = value

  @property
  def fear(self) -> float:
    return self._fear

  @fear.setter
  def fear(self, value: float):
    self._fear = value

  @property
  def joy(self) -> float:
    return self._joy

  @joy.setter
  def joy(self, value: float):
    self._joy = value

  @property
  def sadness(self) -> float:
    return self._sadness

  @sadness.setter
  def sadness(self, value: float):
    self._sadness = value

  def __add__(self, other: floats5):
    return Emotion(
      _anger=self.anger + other[0],
      _disgust=self.disgust + other[1],
      _fear=self.fear + other[2],
      _joy=self.joy + other[3],
      _sadness=self.sadness + other[4],
    )

  def __sub__(self, other: floats5):
    return Emotion(
      _anger=self.anger - other[0],
      _disgust=self.disgust - other[1],
      _fear=self.fear - other[2],
      _joy=self.joy - other[3],
      _sadness=self.sadness - other[4],
    )

  def __mul__(self, other: float):
    return Emotion(
      _anger=self.anger * other,
      _disgust=self.disgust * other,
      _fear=self.fear * other,
      _joy=self.joy * other,
      _sadness=self.sadness * other,
    )

  def __truediv__(self, other: float):
    return Emotion(
      _anger=self.anger / other,
      _disgust=self.disgust / other,
      _fear=self.fear / other,
      _joy=self.joy / other,
      _sadness=self.sadness / other,
    )

  def __str__(self):
    emo = self.normalized
    magnitude = self.magnitude

    if magnitude < 0.4:
      return "平静な様子"

    return f"怒り{emo.anger * 100:.0f}%、嫌悪感{emo.disgust * 100:.0f}%、恐怖{emo.fear * 100:.0f}%、喜び{emo.joy * 100:.0f}%、悲しみ{emo.sadness * 100:.0f}%"
