import json, logging
import numpy as np
from msdm.core.problemclasses.stochasticgame import StochasticGame
from msdm.core.assignment.assignmentset import AssignmentSet as Set
logger = logging.getLogger(__name__)

class TabularStochasticGame(StochasticGame):
    
    def __init__(self,agent_names,memoize=True):
        super(TabularStochasticGame,self).__init__(agent_names=agent_names,memoize=memoize)
    
    @property
    def state_list(self):
        try:
            return self._states
        except AttributeError:
            pass
        logger.info("State space unspecified; performing reachability analysis.")
        self._states = \
            sorted(self.reachable_states(),
                key=lambda d: json.dumps(d, sort_keys=True) if isinstance(d, dict) else d
            )
        return self._states
    
    
    @property
    def joint_action_list(self):
        try:
            return self._joint_actions
        except AttributeError:
            pass
        logger.info("Action space unspecified; performing reachability analysis.")
        actions = Set([])
        for s in self.state_list:
            for ja in self.joint_action_dist(s).support:
                actions.add(ja)
        self._joint_actions = sorted(actions, 
                key=lambda d: json.dumps(d, sort_keys=True) if isinstance(d, dict) else d
            )
        return self._joint_actions
    
    @property
    def transitionmatrix(self):
        try:
            return self._tfmatrix
        except AttributeError:
            pass
        ss = self.state_list
        aa = self.joint_action_list
        tf = np.zeros((len(ss), len(aa), len(ss)))
        for si, s in enumerate(ss):
            for ai, a in enumerate(aa):
                nsdist = self.next_state_dist(s, a)
                for nsi, ns in enumerate(ss):
                    tf[si, ai, nsi] = nsdist.prob(ns)
        self._tfmatrix = tf
        return self._tfmatrix

    @property
    def actionmatrix(self):
        try:
            return self._actmatrix
        except AttributeError:
            pass
        ss = self.state_list
        aa = self.joint_action_list
        am = np.zeros((len(ss), len(aa)))
        for (si, ai), _ in np.ndenumerate(am):
            s, a = ss[si], aa[ai]
            if a in self.joint_action_dist(s).support:
                p = 1
            else:
                p = 0
            am[si, ai] = p
        self._actmatrix = am
        return self._actmatrix


    @property
    def rewardmatrix(self):
        try:
            return self._rfmatrix
        except AttributeError:
            pass
        ss = self.state_list
        aa = self.joint_action_list
        rf = np.zeros((len(ss), len(aa), len(ss),len(self.agent_names)))
        for si, s in enumerate(ss):
            for ai, a in enumerate(aa):
                nsdist = self.next_state_dist(s, a)
                for nsi, ns in enumerate(ss):
                    if ns not in nsdist.support:
                        continue
                    r = self.joint_rewards(s, a, ns)
                    rf[si, ai, nsi] = np.array([r[name] for name in self.agent_names])
        self._rfmatrix = rf
        return self._rfmatrix

    @property
    def stateactionrewardmatrix(self):
        try:
            return self._sarfmatrix
        except AttributeError:
            pass
        rf = self.rewardmatrix
        tf = self.transitionmatrix
        print(rf.shape)
        print(tf.shape)
        self._sarfmatrix = np.einsum("sant,san->sat", rf, tf)
        return self._sarfmatrix

    @property
    def initialstatevec(self):
        try:
            return self._s0vec
        except AttributeError:
            pass
        s0 = self.initial_state_dist()
        self._s0vec = np.array([s0.prob(s) for s in self.state_list])
        return self._s0vec

    @property
    def nonterminalstatevec(self):
        try:
            return self._ntvec
        except AttributeError:
            pass
        ss = self.state_list
        self._ntvec = np.array([0 if self.is_terminal(s) else 1 for s in ss])
        return self._ntvec

    @property
    def reachablestatevec(self):
        try:
            return self._reachablevec
        except AttributeError:
            pass
        reachable = self.reachable_states()
        self._reachablevec = np.array \
            ([1 if s in reachable else 0 for s in self.state_list])
        return self._reachablevec

    @property
    def absorbingstatevec(self):
        try:
            return self._absorbingstatevec
        except AttributeError:
            pass
        def is_absorbing(s):
            actions = self.joint_action_dist(s).support
            for a in actions:
                nextstates = self.next_state_dist(s, a).support
                for ns in nextstates:
                    if not self.is_terminal(ns):
                        return False
            return True
        self._absorbingstatevec = np.array([is_absorbing(s) for s in self.state_list])
        return self._absorbingstatevec

    def reachable_states(self):
        S0 = self.initial_state_dist().support
        frontier = Set(S0)
        visited = Set(S0)
        while len(frontier) > 0:
            s = frontier.pop()
            if self.is_terminal(s):
                continue
            else:
                for ja in self.joint_action_dist(s).support:
                    for ns in self.next_state_dist(s, ja).support:
                        if ns not in visited:
                            frontier.add(ns)
                        visited.add(ns)
        return visited