import math
from fractions import Fraction

from swap_demo_contract.lib.datums_odv import AggState, RewardPrices

# Typical coin precision, such as lovelace for ada
COIN_PRECISION: int = 1_000_000


def median(values: list[int | float], count: int) -> int:
    """
    Calculate the median of a list of values

    Args:
        values: list of numerical values
        count: Number of values

    Returns:
        Median value as an integer

    """
    if len(values) == 1:
        return values[0]

    midpoint = Fraction(1, 2)
    result = quantile(sorted(values), count, midpoint)
    return round_even(result)


def quantile(xs: list[int], n: int, q: Fraction) -> Fraction:
    """
    Calculate the q-th quantile of the sorted list xs

    Args:
        xs: Sorted list of values
        n: Length of the list
        q: Desired quantile (between 0 and 1) as a Fraction

    Returns:
        Quantile value as a Fraction
    """
    n_sub_one = Fraction(n - 1)
    quantile_index = q * n_sub_one

    # Integral part of q * (n - 1)
    j = int(quantile_index // 1)

    # Fractional part of q * (n - 1)
    g = quantile_index - Fraction(j)

    # Get the j-th and (j+1)-th elements
    x_j = xs[j]
    x_j_1 = xs[j + 1] if j + 1 < len(xs) else xs[j]

    # Linear interpolation
    fst = (Fraction(1) - g) * Fraction(x_j)
    snd = g * Fraction(x_j_1)

    return fst + snd


def round_even(num: Fraction) -> int:
    """
    Round to nearest even using Fraction
    """
    floor = int(num // 1)
    decimal = num - floor

    if decimal < Fraction(1, 2):
        return floor
    elif decimal > Fraction(1, 2):
        return floor + 1
    else:
        return floor if floor % 2 == 0 else floor + 1


def scale_rewards_by_rate(reward_prices: RewardPrices, rate_datum: AggState) -> None:
    """Calculate new reward prices based on the fee rate."""
    rate = Fraction(rate_datum.price_data.get_price, COIN_PRECISION)

    def convert_reward(reward: int) -> int:
        return math.ceil(rate * Fraction(reward))

    reward_prices.node_fee = convert_reward(reward_prices.node_fee)
    reward_prices.platform_fee = convert_reward(reward_prices.platform_fee)


def calculate_min_fee_amount(reward_prices: RewardPrices, node_count: int) -> int:
    """Calculate minimum fee amount."""
    try:
        min_fee = reward_prices.platform_fee
        min_fee += reward_prices.node_fee * node_count
        return min_fee
    except Exception as e:
        raise DistributionError(f"Failed to calculate minimum fee: {e}") from e
