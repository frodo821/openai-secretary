from dataclasses import dataclass, field
from datetime import datetime
from random import random
from typing import ClassVar, TypeAlias, overload

floats5: TypeAlias = tuple[float, float, float, float, float] | list[float]


@dataclass(frozen=True)
class EmotionDelta:
  """
  EmotionDelta is a class that represents the change of emotion.
  """
  anger: float
  disgust: float
  fear: float
  joy: float
  sadness: float

  @property
  def magnitude(self) -> float:
    return self @ self

  @property
  def normalized(self) -> 'EmotionDelta':
    return self / self.magnitude

  def __add__(self, other: 'EmotionDelta') -> 'EmotionDelta':
    if not isinstance(other, EmotionDelta):
      return NotImplemented
    return EmotionDelta(
      anger=self.anger + other.anger,
      disgust=self.disgust + other.disgust,
      fear=self.fear + other.fear,
      joy=self.joy + other.joy,
      sadness=self.sadness + other.sadness,
    )

  def __sub__(self, other: 'EmotionDelta') -> 'EmotionDelta':
    if not isinstance(other, EmotionDelta):
      return NotImplemented
    return EmotionDelta(
      anger=self.anger - other.anger,
      disgust=self.disgust - other.disgust,
      fear=self.fear - other.fear,
      joy=self.joy - other.joy,
      sadness=self.sadness - other.sadness,
    )

  def __mul__(self, other: float) -> 'EmotionDelta':
    if not isinstance(other, (float, int)):
      return NotImplemented
    return EmotionDelta(
      anger=self.anger * other,
      disgust=self.disgust * other,
      fear=self.fear * other,
      joy=self.joy * other,
      sadness=self.sadness * other,
    )

  def __truediv__(self, other: float) -> 'EmotionDelta':
    if not isinstance(other, (float, int)):
      return NotImplemented
    return EmotionDelta(
      anger=self.anger / other,
      disgust=self.disgust / other,
      fear=self.fear / other,
      joy=self.joy / other,
      sadness=self.sadness / other,
    )

  def __matmul__(self, other: 'EmotionDelta') -> float:
    if not isinstance(other, EmotionDelta):
      return NotImplemented
    return (
      self.anger * other.anger + self.disgust * other.disgust + self.fear * other.fear + self.joy * other.joy +
      self.sadness * other.sadness
    )

  def __getitem__(self, key: int) -> float:
    return (self.anger, self.disgust, self.fear, self.joy, self.sadness)[key]


@dataclass
class Emotion:
  """
  Emotion is a class that represents the emotion of a simulated consciousness.
  """

  _anger: float
  _disgust: float
  _fear: float
  _joy: float
  _sadness: float
  _frozen: bool = False

  _created: datetime = field(
    default_factory=datetime.now,
    init=False,
    repr=False,
    hash=False,
    compare=False,
  )
  decrease_coefficient: ClassVar[float] = 0.999

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
  def frozen(self) -> 'Emotion':
    if self._frozen:
      return self
    return Emotion(
      _anger=self._anger,
      _disgust=self._disgust,
      _fear=self._fear,
      _joy=self._joy,
      _sadness=self._sadness,
      _frozen=True,
    )

  @property
  def magnitude(self) -> float:
    return (self.anger**2 + self.disgust**2 + self.fear**2 + self.joy**2 + self.sadness**2)**0.5

  @property
  def normalized(self) -> 'Emotion':
    return self / self.magnitude

  def json(self) -> floats5:
    return (self.anger, self.disgust, self.fear, self.joy, self.sadness)

  @property
  def attenuation(self) -> float:
    if self._frozen:
      return 1.0
    return self.decrease_coefficient**(datetime.now() - self._created).total_seconds()

  @property
  def anger(self) -> float:
    return self._anger * self.attenuation

  @anger.setter
  def anger(self, value: float) -> None:
    self._anger = value

  @property
  def disgust(self) -> float:
    return self._disgust * self.attenuation

  @disgust.setter
  def disgust(self, value: float) -> None:
    self._disgust = value

  @property
  def fear(self) -> float:
    return self._fear * self.attenuation

  @fear.setter
  def fear(self, value: float) -> None:
    self._fear = value

  @property
  def joy(self) -> float:
    return self._joy * self.attenuation

  @joy.setter
  def joy(self, value: float) -> None:
    self._joy = value

  @property
  def sadness(self) -> float:
    return self._sadness * self.attenuation

  @sadness.setter
  def sadness(self, value: float) -> None:
    self._sadness = value

  def __add__(self, other: floats5 | EmotionDelta) -> 'Emotion':
    return Emotion(
      _anger=self.anger + other[0],
      _disgust=self.disgust + other[1],
      _fear=self.fear + other[2],
      _joy=self.joy + other[3],
      _sadness=self.sadness + other[4],
    )

  @overload
  def __sub__(self, other: 'Emotion') -> EmotionDelta:
    ...

  @overload
  def __sub__(self, other: floats5 | EmotionDelta) -> 'Emotion':
    ...

  def __sub__(self, other):
    if isinstance(other, Emotion):
      return EmotionDelta(
        anger=self.anger - other.anger,
        disgust=self.disgust - other.disgust,
        fear=self.fear - other.fear,
        joy=self.joy - other.joy,
        sadness=self.sadness - other.sadness,
      )

    if not isinstance(other, (tuple, list, EmotionDelta)):
      return NotImplemented

    return Emotion(
      _anger=self.anger - other[0],
      _disgust=self.disgust - other[1],
      _fear=self.fear - other[2],
      _joy=self.joy - other[3],
      _sadness=self.sadness - other[4],
    )

  def __mul__(self, other: float) -> 'Emotion':
    return Emotion(
      _anger=self.anger * other,
      _disgust=self.disgust * other,
      _fear=self.fear * other,
      _joy=self.joy * other,
      _sadness=self.sadness * other,
    )

  def __truediv__(self, other: float) -> 'Emotion':
    return Emotion(
      _anger=self.anger / other,
      _disgust=self.disgust / other,
      _fear=self.fear / other,
      _joy=self.joy / other,
      _sadness=self.sadness / other,
    )

  def __str__(self) -> str:
    emo = self.normalized
    magnitude = self.magnitude

    if magnitude < 0.4:
      return "平静な様子"

    return f"怒り{emo.anger * 100:.0f}%、嫌悪感{emo.disgust * 100:.0f}%、恐怖{emo.fear * 100:.0f}%、喜び{emo.joy * 100:.0f}%、悲しみ{emo.sadness * 100:.0f}%"
