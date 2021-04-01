from abc import ABC, abstractmethod
from typing import Iterable, Any, TypeVar, Generic, Tuple
import random
import math
from collections import defaultdict

Event = TypeVar('Event')

class Distribution(ABC, Generic[Event]):
    @abstractmethod
    def sample(self) -> Event:
        pass

class FiniteDistribution(Distribution):
    @abstractmethod
    def prob(self, e: Event) -> float:
        pass

    @property
    @abstractmethod
    def support(self) -> Iterable[Event]:
        pass

    def sample(self) -> Event:
        support = self.support
        if not isinstance(support, (list, tuple)):
            support = tuple(support)
        if len(support) == 1:
            return support[0]
        return random.choices(
            population=support,
            weights=tuple(self.probs),
            k=1
        )[0]

    def items(self) -> Iterable[Tuple[Event, float]]:
        for e in self.support:
            yield e, self.prob(e)

    @property
    def probs(self) -> Iterable[float]:
        yield from (self.prob(e) for e in self.support)

    def score(self, e: Event) -> float:
        p = self.prob(e)
        if p == 0:
            return -float('inf')
        return math.log(p)

    def __and__(self, other: "FiniteDistribution[Event]") -> "FiniteDistribution[Event]":
        """Conjunction"""
        newdist = defaultdict(float)
        norm = 0
        for e in set(self.support) & set(other.support):
            newdist[e] += self.score(e)
            newdist[e] += other.score(e)
            norm += math.exp(newdist[e])
        lognorm = math.log(norm)
        return DictDistribution({e: math.exp(l - lognorm) for e, l in newdist.items()})

    def __or__(self, other: "FiniteDistribution[Event]") -> "FiniteDistribution[Event]":
        """Disjunction/Mixture"""
        newdist = defaultdict(float)
        for e, p in self.items():
            newdist[e] += p
        for e, p in other.items():
            newdist[e] += p
        return DictDistribution(newdist)

    def __mul__(self, num: float):
        return DictDistribution({e: p*num for e, p in self.items()})

    def __repr__(self):
        e_p = ", ".join([f"{e}: {p}" for e, p in self.items()])
        return f"{self.__class__.__name__}({{{e_p}}})"

    def isclose(self, other: "FiniteDistribution[Event]") -> bool:
        mapped = {
            s: p
            for s, p in self.items()
        }
        for s, p in other.items():
            if not math.isclose(p, mapped.get(s, 0.0)):
                return False
        return True

# Importing down here to avoid a cyclic reference.
from msdm.core.distributions.dictdistribution import DictDistribution
