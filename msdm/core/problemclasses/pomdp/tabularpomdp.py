import logging
from abc import abstractmethod, ABC
from typing import Set, Sequence, Hashable, Mapping, TypeVar
import numpy as np

from msdm.core.utils.funcutils import method_cache, cached_property
from msdm.core.problemclasses.pomdp.pomdp import PartiallyObservableMDP
from msdm.core.problemclasses.mdp import TabularMarkovDecisionProcess
from msdm.core.distributions import FiniteDistribution, DictDistribution

logger = logging.getLogger(__name__)

HashableObservation = TypeVar('HashableObservation', bound=Hashable)

class TabularPOMDP(TabularMarkovDecisionProcess, PartiallyObservableMDP):
    def as_matrices(self):
        return {
            'ss': self.state_list,
            'aa': self.action_list,
            'tf': self.transition_matrix,
            'rf': self.reward_matrix,
            'sarf': self.state_action_reward_matrix,
            's0': self.initial_state_vec,
            'nt': self.nonterminal_state_vec,
            'rs': self.reachable_state_vec,
            'ast': self.absorbing_state_vec,
            'obs': self.observation_matrix
        }

    @cached_property
    def observation_list(self) -> Sequence[HashableObservation]:
        """
        List of observations. Note that ordering is only guaranteed to be
        consistent for a particular instance.
        """
        logger.info("Observation space unspecified; performing reachability analysis.")
        obs = set([])
        for a in self.action_list:
            for ns in self.state_list:
                obs.update([o for o, p in self.observation_dist(a, ns).items() if p > 0.])
        try:
            return sorted(obs)
        except TypeError: #unsortable representation
            pass
        return list(obs)

    @method_cache
    def _cached_observation_dist(self, a, ns) -> FiniteDistribution:
        '''
        We prefer using this cached version of observation_dist when possible.
        '''
        return self.observation_dist(a, ns)

    @cached_property
    def observation_index(self) -> Mapping[HashableObservation, int]:
        return {o: i for i, o in enumerate(self.observation_list)}

    @cached_property
    def observation_matrix(self) -> np.array:
        aa = self.action_list
        nss = self.state_list
        oo = self.observation_list
        ooi = self.observation_index
        obs = np.zeros((len(aa), len(nss), len(oo)))
        for ai, a in enumerate(self.action_list):
            for nsi, ns in enumerate(self.state_list):
                for o, p in self._cached_observation_dist(a, ns).items():
                    obs[ai, nsi, ooi[o]] = p
        return obs
