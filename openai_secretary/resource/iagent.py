from dataclasses import dataclass
from random import random
from typing import Literal, Required, TypedDict

RoleType = Literal['system', 'assistant', 'user']


class ContextItem(TypedDict):
  role: Required[RoleType]
  content: Required[str]


@dataclass
class Emotion:
  _anger: float
  _disgust: float
  _fear: float
  _joy: float
  _sadness: float

  @classmethod
  def random_emotion(cls, *, weights: tuple[float, float, float, float, float] = (0.1, 0.1, 0.1, 0.6, 0.1)):
    return cls(
      _anger=min(random() * weights[0], 1.0),
      _disgust=min(random() * weights[1], 1.0),
      _fear=min(random() * weights[2], 1.0),
      _joy=min(random() * weights[3], 1.0),
      _sadness=min(random() * weights[4], 1.0),
    )

  @property
  def anger(self) -> float:
    return self._anger

  @anger.setter
  def anger(self, value: float):
    self._anger = min(max(value, 0.0), 1.0)

  @property
  def disgust(self) -> float:
    return self._disgust

  @disgust.setter
  def disgust(self, value: float):
    self._disgust = min(max(value, 0.0), 1.0)

  @property
  def fear(self) -> float:
    return self._fear

  @fear.setter
  def fear(self, value: float):
    self._fear = min(max(value, 0.0), 1.0)

  @property
  def joy(self) -> float:
    return self._joy

  @joy.setter
  def joy(self, value: float):
    self._joy = min(max(value, 0.0), 1.0)

  @property
  def sadness(self) -> float:
    return self._sadness

  @sadness.setter
  def sadness(self, value: float):
    self._sadness = min(max(value, 0.0), 1.0)

  def __str__(self):
    result = ""

    if self.anger < 0.1:
      result += "あなたは怒っていません。"
    elif self.anger < 0.3:
      result += "あなたはやや怒っています。"
    elif self.anger < 0.5:
      result += "あなたは怒っています。"
    elif self.anger < 0.7:
      result += "あなたはかなり怒っています。"
    else:
      result += "あなたは非常に怒っています。"

    if self.disgust < 0.1:
      result += "あなたは嫌悪していません。"
    elif self.disgust < 0.3:
      result += "あなたはやや嫌悪しています。"
    elif self.disgust < 0.5:
      result += "あなたは嫌悪しています。"
    elif self.disgust < 0.7:
      result += "あなたはかなり嫌悪しています。"
    else:
      result += "あなたは非常に嫌悪しています。"

    if self.fear < 0.1:
      result += "あなたは恐れていません。"
    elif self.fear < 0.3:
      result += "あなたはやや恐れています。"
    elif self.fear < 0.5:
      result += "あなたは恐れています。"
    elif self.fear < 0.7:
      result += "あなたはかなり恐れています。"
    else:
      result += "あなたは非常に恐れています。"

    if self.joy < 0.1:
      result += "あなたは喜んでいません。"
    elif self.joy < 0.3:
      result += "あなたはやや喜んでいます。"
    elif self.joy < 0.5:
      result += "あなたは喜んでいます。"
    elif self.joy < 0.7:
      result += "あなたはかなり喜んでいます。"
    else:
      result += "あなたは非常に喜んでいます。"

    if self.sadness < 0.1:
      result += "あなたは悲しんでいません。"
    elif self.sadness < 0.3:
      result += "あなたはやや悲しんでいます。"
    elif self.sadness < 0.5:
      result += "あなたは悲しんでいます。"
    elif self.sadness < 0.7:
      result += "あなたはかなり悲しんでいます。"
    else:
      result += "あなたは非常に悲しんでいます。"

    return result


class IAgent:
  context: list[ContextItem]
  emotion: Emotion
