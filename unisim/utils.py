"""
Various functions to calculate prices, etc...
"""

import math

Q96 = 2**96
TICK_BASE = 1.0001

MIN_TICK = -887272
MAX_TICK = 887272


def as_18(value: float) -> int:
    """
    Convert a price into 18 decimal places
    """
    return int(value * 1e18)


def from_18(value: int) -> float:
    """
    Convert a value from 18 decimal places
    """
    return value / 1e18


def are_sorted_tokens(t0_address, t1_address) -> bool:
    """
    Check of addresses are sorted
    """
    return bytes.fromhex(t0_address[2:]) < bytes.fromhex(t1_address[2:])


def is_tick_in_range(tick: int) -> bool:
    """
    Check a tick is in a valid range
    """
    return tick >= MIN_TICK and tick <= MAX_TICK


def sqrtp_to_price(sqrtpvalue: int) -> int:
    """
    Given sqrtp from slot0 return the price

    The value from slot0 is the exchange rate price of token1:
    "how much token1 does it cost to but 1 token0"
    """
    return (sqrtpvalue / Q96) ** 2


def price_to_sqrtp(token1price: float) -> int:
    """
    Get the sqrt price for the given token price.

    `value` should be the true format - without offsetting for 1e18 (DECIMALS)
    """
    return int(math.sqrt(token1price) * Q96)


def price_to_tick(token1price: float) -> int:
    """
    Get the tick index given the token1 price
    """
    return math.floor(math.log(token1price, TICK_BASE))


def price_to_tick_with_spacing(price, spacing=10):
    """
    Convert a price to a tick and offset for the spacing
    """
    tick = price_to_tick(price)
    return math.floor(tick / spacing) * spacing


def tick_to_price(tick: int) -> float:
    """
    Return the token1 price from the given tick

    Note: tick prices are not as accurate as the square root price
    (this should also mulitply 2**96 to be in sqrtp format...)
    """
    return TICK_BASE**tick


def tick_to_sqrtx96(tick):
    """
    Convert a ticks to sqrtX96 price format
    """
    return int((TICK_BASE ** (tick / 2)) * Q96)


def liquidity0(amount, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    denominator = pb - pa
    assert denominator > 0, "denominator must be > 0"
    return (amount * (pa * pb) / Q96) / denominator


def liquidity1(amount, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    denominator = pb - pa
    assert denominator > 0, "denominator must be > 0"
    return amount * Q96 / denominator


def get_liquidity_for_amounts(sqrtC, sqrtA, sqrtB, amount0, amount1):
    if sqrtA > sqrtB:
        sqrtA, sqrtB = sqrtB, sqrtA

    if sqrtC <= sqrtA:
        liq = liquidity0(amount0, sqrtA, sqrtB)
    elif sqrtC < sqrtB:
        liq0 = liquidity0(amount0, sqrtC, sqrtB)
        liq1 = liquidity1(amount1, sqrtA, sqrtC)
        if liq0 < liq1:
            liq = liq0
        else:
            liq = liq1
    else:
        liq = liquidity1(amount1, sqrtA, sqrtB)

    return liq


def calc_amount0(liq, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    return int(liq * Q96 * (pb - pa) / pb / pa)


def calc_amount1(liq, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    return int(liq * (pb - pa) / Q96)


def get_amounts_for_liquidity(liq, sqrtC, sqrtA, sqrtB):
    if sqrtA > sqrtB:
        sqrtA, sqrtB = sqrtB, sqrtA

    amount0 = 0
    amount1 = 0
    if sqrtC <= sqrtA:
        amount0 = calc_amount0(liq, sqrtA, sqrtB)
    elif sqrtC < sqrtB:
        amount0 = calc_amount0(liq, sqrtC, sqrtB)
        amount1 = calc_amount1(liq, sqrtA, sqrtC)
    else:
        amount1 = calc_amount1(liq, sqrtA, sqrtB)

    return (amount0, amount1)
