from fractions import Fraction
from math import ceil

import pytest

from utils.fee import split_fee

SEEDED_BPS = [99, 199, 299]
EDGE_BPS = [0, 1, 9999, 10000]


class TestSplitFee:
    def test_card_example(self):
        assert split_fee(11000, 299) == (329, 10671)

    def test_exact_division_has_no_rounding(self):
        assert split_fee(10000, 299) == (299, 9701)

    def test_rounds_fee_up(self):
        assert split_fee(101, 99) == (1, 100)
        assert split_fee(1, 1) == (1, 0)

    def test_zero_fee(self):
        assert split_fee(12345, 0) == (0, 12345)

    def test_full_fee(self):
        assert split_fee(12345, 10000) == (12345, 0)

    def test_invariant_fee_plus_net_equals_amount(self):
        for fee_bps in SEEDED_BPS + EDGE_BPS:
            for amount_minor in range(1, 20001):
                fee_minor, net_minor = split_fee(amount_minor, fee_bps)
                assert fee_minor + net_minor == amount_minor
                assert 0 <= fee_minor <= amount_minor
                assert net_minor >= 0

    def test_fee_is_exact_ceiling(self):
        for fee_bps in SEEDED_BPS + EDGE_BPS:
            for amount_minor in range(1, 20001):
                fee_minor, _ = split_fee(amount_minor, fee_bps)
                assert fee_minor * 10000 >= amount_minor * fee_bps
                assert (fee_minor - 1) * 10000 < amount_minor * fee_bps

    def test_large_amounts_do_not_lose_precision(self):
        amount_minor = 9_007_199_254_740_993
        fee_minor, net_minor = split_fee(amount_minor, 299)
        assert fee_minor == ceil(Fraction(amount_minor * 299, 10000))
        assert fee_minor + net_minor == amount_minor

    def test_refuses_float_amount(self):
        with pytest.raises(TypeError):
            split_fee(110.0, 299)

    def test_refuses_float_bps(self):
        with pytest.raises(TypeError):
            split_fee(11000, 2.99)

    def test_refuses_non_positive_amount(self):
        with pytest.raises(ValueError):
            split_fee(0, 299)

    def test_refuses_bps_out_of_range(self):
        with pytest.raises(ValueError):
            split_fee(11000, 10001)
