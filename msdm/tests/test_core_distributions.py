import unittest
import warnings
import random
import numpy as np
import pandas as pd
from scipy.special import softmax
from msdm.core.distributions import DiscreteFactorTable, DictDistribution,\
    UniformDistribution, DeterministicDistribution, SoftmaxDistribution

def toDF(p):
    df = pd.DataFrame(p.support)
    df['prob'] = p.probs
    df['scores'] = p.scores
    return df

np.seterr(divide='ignore')
Pr = DiscreteFactorTable

class DistributionTestCase(unittest.TestCase):
    def test_basics(self):
        for cls in [DiscreteFactorTable]:
            print(cls)
            dist = cls({0: 0, 1: 1}) # Can construct with a logit dict
            assert dist == cls([0, 1], logits=[0, 1]) # or explicitly
            assert dist == cls([0, 1], scores=[0, 1]) # or explicitly

            # Per Python convention for repr, we ensure we can evaluate to the same.
            assert eval(repr(dist)) == dist

            # Testing close but not identical ones.
            dist_close = cls([0, 1], logits=[0, 1.000001])
            assert dist != dist_close
            assert dist.isclose(dist_close)

            # Testing case where logits differ but describe same probability dist
            dist_logit_fixed_dist = cls([0, 1], logits=[100, 101])
            assert dist != dist_close
            assert dist.isclose(dist_close)

            # Testing case where keys are out of order
            dist_logit_fixed_dist = cls([1, 0], logits=[1, 0])
            assert dist != dist_close
            assert dist.isclose(dist_close)

            # Can do isclose to probabilities
            assert dist.isclose(cls([0, 1], probs=softmax([1, 2])))

            # Testing uniform distribution
            assert cls([0, 1, 2]).isclose(cls([0, 1, 2], logits=[1, 1, 1]))

    def test_softmax_distribution(self):
        scores = {'a': 100, 'b': 100, 'c': 90, 'd': 50}
        for _ in range(20):
            r = random.randint(0, 1000)
            new_scores = {e: s - r for e, s in scores.items()}
            assert SoftmaxDistribution(scores).isclose(SoftmaxDistribution(new_scores))
            assert sum(SoftmaxDistribution(new_scores).values()) == 1.0

    def test_dictdistribution(self):
        dd1 = DictDistribution(a=.1, b=.2, c=.7)
        dd2 = DictDistribution(d=1)
        assert (dd2 * .5 | dd1 * .5) == {'d': 0.5, 'a': 0.05, 'b': 0.1, 'c': 0.35}

        dd1 = DictDistribution(a=.1, b=.2, c=.7)
        dd2 = DictDistribution(a=.5, b=.5)
        assert (dd1 & dd2) == {'b': 2/3, 'a': 1/3}

        assert (dd1 & dd2).isclose(DictDistribution({'b': 2/3, 'a': 1/3}))

    def test_or_mul(self):
        avals = [DictDistribution({'a': 1}), UniformDistribution(['a']), DeterministicDistribution('a')]
        bvals = [DictDistribution({'b': 1}), UniformDistribution(['b']), DeterministicDistribution('b')]
        for adist in avals:
            assert (adist * 0.5).isclose(DictDistribution({'a': 0.5}))
            for bdist in bvals:
                assert (adist * 0.5 | bdist * 0.5).isclose(UniformDistribution(['a', 'b']))

    def test_and(self):
        ds = [DictDistribution({'a': 0.5, 'b': 0.5}), UniformDistribution(['a', 'b'])]
        for d in ds:
            res = d & DictDistribution({'a': 0.5, 'b': 0.25, 'c': 0.25})
            assert res.isclose(DictDistribution({'a': 2/3, 'b': 1/3}))

    def test_uniform_and_deterministic_dist(self):
        assert DictDistribution(a=0.5, b=0.5).isclose(DictDistribution.uniform(['a', 'b']))
        assert DictDistribution(a=1).isclose(DictDistribution.deterministic('a'))

    def test_sample(self):
        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
        for cls in [DiscreteFactorTable]:
            np.random.seed(42)
            assert cls([]).sample() is None
            assert cls([0]).sample() == 0
            assert {cls([0, 1]).sample() for _ in range(20)} == {0, 1}
        warnings.filterwarnings("default", category=PendingDeprecationWarning)

    def test_independent_conjunction(self):
        # Conjunction (independent variables)
        pA = Pr([{'a': 0}, {'a': 1}], probs=[.9, .1])
        pB = Pr([{'b': 0}, {'b': 1}], probs=[.5, .5])
        p = pA & pB
        assert all(np.isclose(
            toDF(p).sort_values(['a', 'b'])['prob'],
            [.45, .45, .05, .05]
        ))

    def test_overlapping_conjunction(self):
        # Conjunction
        pA1 = Pr([{'a': 0}, {'a': 1}, {'a': 2}], probs=[.7, .2, .1])
        pA2 = Pr([{'a': 1}, {'a': 2}, {'a': 3}], probs=[.5, .4, .1])
        p = pA1 & pA2
        pp = np.array([.2 * .5, .1 * .4])
        pp = pp / pp.sum()
        assert all(np.isclose(
            toDF(p.normalize()).sort_values(['a'])['prob'],
            pp)
        )

    def test_dependent_conjunction(self):
        # Conjunction (dependent variables)
        pAB = Pr([{'a': 0, 'b': 0}, {'a': 1, 'b': 1}], probs=[.9, .1])
        pB = Pr([{'b': 0}, {'b': 1}], probs=[1 / 3, 2 / 3])
        p = pAB & pB
        pp = np.array([.9 * (1 / 3), .1 * (2 / 3)])
        pp = pp / pp.sum()
        assert all(np.isclose(
            toDF(p.normalize()).sort_values(['a', 'b'])['prob'],
            pp
        ))

    def test_dependent_conjunction2(self):
        # Conjunction (dependent variables)
        pAB = Pr([{'a': 0, 'b': 0}, {'a': 1, 'b': 1}], probs=[.9, .1])
        pBC = Pr([{'b': 0, 'c': 0}, {'b': 1, 'c': 0}, {'b': 1, 'c': 1}],
                 probs=[1 / 3, 1 / 3, 1 / 3])
        p = pAB & pBC
        pp = np.array([.9 * (1 / 3), .1 * (1 / 3), .1 * (1 / 3)])
        pp = pp / pp.sum()
        assert all(np.isclose(
            toDF(p.normalize()).sort_values(['a', 'b'])['prob'],
            pp
        ))

    def test_disjunction(self):
        # Mixture of Distributions
        pA1 = Pr([{'a': 0}, {'a': 1}], probs=[.9, .1])
        pA2 = Pr([{'a': 1}, {'a': 2}], probs=[.5, .5])
        p = pA1 * .1 | pA2 * .9
        pp = np.array([.9 * .1, (.1 * .1 + .5 * .9), .5 * .9])
        assert all(np.isclose(
            toDF(p.normalize()).sort_values(['a'])['prob'],
            pp
        ))

    def test_marginalization(self):
        # marginalization
        pA = Pr([{'a': 0}, {'a': 1}], probs=[.9, .1])
        pB = Pr([{'b': 0}, {'b': 1}], probs=[.1, .9])
        pAB = pA & pB
        pAeqB = pAB[lambda r: "a == b" if r['a'] == r['b'] else "a != b"]
        pp = np.array([.9 * .1 + .9 * .1, 1 - (.9 * .1 + .9 * .1)])
        assert all(np.isclose(
            toDF(pAeqB)['prob'],
            pp
        ))

if __name__ == '__main__':
    unittest.main()
