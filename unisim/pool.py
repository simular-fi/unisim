"""
Uniswap v3 pool.  Represents a token pair and fee schedule.
For simplicty, all tokens use 10^18 decimals.
"""

import polars as pl
from typing import Tuple
from dataclasses import dataclass

from unisim.abis import uniswap_token
from unisim.utils import (
    price_to_sqrtp,
    sqrtp_to_price,
    price_to_tick_with_spacing,
    as_18,
    from_18,
    are_sorted_tokens,
)
from simular import PyEvm, Contract, contract_from_inline_abi

# purposely far in the future to make
# sure the trade is within the deadline.
EXECUTE_SWAP_DEADLINE = int(1e32)

# Uniswap v3 fee schedule and spacing
FEE_RANGE = [100, 500, 3000, 10_000]
FEE_TICK_SPACING = [1, 10, 60, 200]


def get_spacing_for_fee(fee: int) -> int:
    """
    Return the tick spacing for the given fee
    """
    assert fee in FEE_RANGE, "not a valid fee"
    return FEE_TICK_SPACING[FEE_RANGE.index(fee)]


def get_fee_for_spacing(spacing: int) -> int:
    """
    Return the fee for the given tick spacing
    """
    assert spacing in FEE_TICK_SPACING, "not a valid tick spacing"
    return FEE_RANGE[FEE_TICK_SPACING.index(spacing)]


@dataclass
class Token:
    """
    Meta information for a token
    """

    symbol: str
    start_price: 1

    @property
    def initial_price(self):
        return as_18(self.start_price)


def pool_contract(evm):
    """helper to provide pool interface"""
    return contract_from_inline_abi(
        evm,
        [
            "function liquidity()(uint128)",
            "function slot0()(uint160,int24,uint16,uint16,uint16,uint8,bool)",
        ],
    )


@dataclass
class DataCollector:
    """
    Used to collect data from a pool and convert into a dataframe
    """

    token0_symbol: str
    token1_symbol: str
    t0_current_volume = 0
    t1_current_volume = 0
    step = []
    tick = []
    t0_price = []
    t1_price = []
    t0_volume = []
    t1_volume = []
    t0_reserves = []
    t1_reserves = []

    def add_volume(self, t0, t1):
        """
        Usually call by the agent on a step
        """
        self.t0_current_volume += t0
        self.t1_current_volume += t1

    def collect_volume(self):
        """
        Called at the end of the step to aggregate volume
        across agents and clear values for next step.
        """
        self.t0_volume.append(self.t0_current_volume / 1e18)
        self.t1_volume.append(self.t1_current_volume / 1e18)
        # clear for next step
        self.t0_current_volume = 0
        self.t1_current_volume = 0

    def into_dataframe(self):
        """
        Convert data to a Dataframe
        """
        return pl.DataFrame(
            [
                self.step,
                self.tick,
                self.t0_price,
                self.t1_price,
                self.t0_volume,
                self.t1_volume,
                self.t0_reserves,
                self.t1_reserves,
            ],
            schema={
                "steps": pl.Int32,
                "ticks": pl.Int32,
                f"{self.token0_symbol}_price": pl.Float64,
                f"{self.token1_symbol}_price": pl.Float64,
                f"{self.token0_symbol}_vol": pl.Float64,
                f"{self.token1_symbol}_vol": pl.Float64,
                f"{self.token0_symbol}_reserve": pl.Float64,
                f"{self.token1_symbol}_reserve": pl.Float64,
            },
        )


class Pool:
    """
    Represents a pool in Uniswap v3. Contains the core functionality to interact with the pool:
    - create a pair
    - mint an NFT position
    - add/remove liquidity to a position
    - mint/burn tokens for the given pool
    - collect data
    A given model may have many pools
    """

    name: str  # auto-generated: e.g. DAI_USDC_500
    step: int  # this is the model step
    token0: Contract
    token1: Contract
    fee: int
    router: Contract
    nftposition: Contract
    pool_contract: Contract

    def __init__(
        self,
        _evm: PyEvm,
        _token_a: Token,
        _token_b: Token,
        _fee: int,
        _router: Contract,
        _nftposition: Contract,
        _deployer_address: str,
    ):
        """
        Create and deploy a new pool
        """
        assert _fee in FEE_RANGE, "Not a valid pool fee"
        assert (
            _token_b.start_price == 1
        ), "token b should always have a starting price of 1"

        self.name = f"{_token_a.symbol}_{_token_b.symbol}_{_fee}"
        self.step = 0
        self.fee = _fee
        self.router = _router
        self.nftposition = _nftposition

        _a = uniswap_token(_evm)
        _b = uniswap_token(_evm)
        _a.deploy(_token_a.symbol, caller=_deployer_address)
        _b.deploy(_token_b.symbol, caller=_deployer_address)

        # Addresses are required to be sorted. If not, it can
        # cause a pool key issue.  We sort the addresses here
        # and re-assign symbol names if needed to match the
        # initial input
        if bytes.fromhex(_a.address[2:]) < bytes.fromhex(_b.address[2:]):
            self.token0 = _a
            self.token1 = _b
        else:
            self.token0 = _b
            self.token0.update_symbol.transact(
                _token_a.symbol, caller=_deployer_address
            )
            self.token1 = _a
            self.token1.update_symbol.transact(
                _token_b.symbol, caller=_deployer_address
            )

        # calculate initial price as SQRTPx96
        sqrtp = price_to_sqrtp(_token_b.initial_price / _token_a.initial_price)

        # create the pool
        pool_address = self.nftposition.createAndInitializePoolIfNecessary.transact(
            self.token0.address,
            self.token1.address,
            _fee,
            sqrtp,
            caller=_deployer_address,
        ).output
        self.pool_contract = pool_contract(_evm).at(pool_address)

        # set up the datacollector
        self.data = DataCollector(_token_a.symbol, _token_b.symbol)

    def get_sqrtp_tick(self) -> Tuple[int, int]:
        """
        Returns the current sqrtpX96 price and active tick
        """
        slot_info = self.pool_contract.slot0.call()
        return (slot_info[0], slot_info[1])

    def exchange_prices(self) -> Tuple[float, float]:
        """
        Returns the current prices adjusted for decimal places:
        (price of token0, price of token1)
        """
        sqrtp, _ = self.get_sqrtp_tick()
        t1 = sqrtp_to_price(sqrtp)
        t0 = 1e18 / t1 / 1e18
        return (t0, t1)

    def mint_tokens(self, amt_t0, amt_t1, agent):
        """
        Helper to mint the tokens used be the pool for the given agent.
        This is needed for swaps/liquidity calls, etc...

        Input amounts are automatically scaled for the token's decimal places.

        Args:
         - amt_to: amount of token0
         - amt_t1: amount of token1
         - agent : who the tokens are for
        """
        at0 = as_18(amt_t0)
        at1 = as_18(amt_t1)

        self.token0.mint.transact(agent, at0, caller=agent)
        self.token1.mint.transact(agent, at1, caller=agent)

    def burn_tokens(self, amt_t0, amt_t1, agent):
        """
        Burn tokens for the given agent.  You can only burn what you own

        Args:
        - amount of token0 to burn
        - amount of token1 to burn
        - caller
        """
        at0 = as_18(amt_t0)
        at1 = as_18(amt_t1)

        bal0 = self.token0.balanceOf.call(agent)
        bal1 = self.token1.balanceOf.call(agent)

        if at0 > 0 and bal0 >= at0:
            self.token0.burn.transact(agent, at0, caller=agent)
        if at1 > 0 and bal1 >= at1:
            self.token1.burn.transact(agent, at1, caller=agent)

    def pair_balance(self, owner: str) -> Tuple[int, int]:
        """
        Args:
         - owner address

        Returns: both token0 and token1 balances for 'owner'.  Balances
        are automatically scaled down from decimal places
        """
        bal0 = self.token0.balanceOf.call(owner)
        bal1 = self.token1.balanceOf.call(owner)
        return (
            from_18(bal0),
            from_18(bal1),
        )

    def reserves(self) -> Tuple[int, int]:
        """
        Returns the pool's reserve balances for each token
        """
        return self.pair_balance(self.pool_contract.address)

    def mint_position(
        self, token0_amount, token1_amount, low_price, high_price, agent
    ) -> Tuple[int, int, int]:
        """
        Mint a new position in the pool.

        Args:
        - amount of token0 to mint
        - amount of token1 to mint
        - low price range for the position
        - high price range for the position
        - Caller

        Returns:
        - actual amount used for token0
        - actual amount used for token1
        - NFT token ID
        """
        bal0, bal1 = self.pair_balance(agent)
        assert bal0 >= token0_amount and bal1 >= token1_amount, "insufficient balance"

        # check token addresses are sorted.  This is done automatically when creating the pool
        assert are_sorted_tokens(
            self.token0.address, self.token1.address
        ), "token pair are not sorted"

        t0amt = as_18(token0_amount)
        t1amt = as_18(token1_amount)

        # adjust and sort ticks
        spacing = get_spacing_for_fee(self.fee)
        lowtick = price_to_tick_with_spacing(1e18 / as_18(low_price), spacing)
        hightick = price_to_tick_with_spacing(1e18 / as_18(high_price), spacing)
        if lowtick > hightick:
            lowtick, hightick = hightick, lowtick

        # approve the nft manager to move tokens on our behalf
        self.token0.approve.transact(self.nftposition.address, t0amt, caller=agent)
        self.token1.approve.transact(self.nftposition.address, t1amt, caller=agent)

        # mint the liquidity
        token_id, _liq, a0, a1 = self.nftposition.mint.transact(
            (
                self.token0.address,
                self.token1.address,
                self.fee,
                lowtick,
                hightick,
                t0amt,
                t1amt,
                0,
                0,
                agent,
                int(2e34),
            ),  # the 2000... number is just a deadline we set high
            caller=agent,
        ).output

        return (a0, a1, token_id)

    def get_position(self, token_id: int) -> Tuple[int, int, int, int]:
        """
        Get position information for a given LP.

        Args:
        - token ID

        Returns:
        - pool fee
        - lower tick
        - upper tick
        - liquidity
        """
        _, _, _, _, fee, tl, tu, liq, _, _, _, _ = self.nftposition.positions.call(
            token_id
        )
        return fee, tl, tu, liq

    def increase_liquidity(
        self,
        token_id: int,
        amount0: float,
        amount1: float,
        agent: str,
    ):
        """
        Increase the liquidity of a position for a given tokenid.  Tokenid
        cooresponds to an existing minted position for the sender (agent).

        Args:
         - token ID for the position
         - amount0: the amount of token0 to increase
         - amount1: the amount of token1 to increase
         - agent: the caller address that's the owner of the position

        Returns:
          - liquidity: the new amount of liquidity for the position
          - amt0: the actual amount of token0 used
          - amt1: the actual amount of token1 used
        """
        amt0 = as_18(amount0)
        amt1 = as_18(amount1)

        # approve the nft manager to move tokens on our behalf
        self.token0.approve.transact(self.nftposition.address, amt0, caller=agent)
        self.token1.approve.transact(self.nftposition.address, amt1, caller=agent)

        liq, a0, a1 = self.nftposition.increaseLiquidity.transact(
            (token_id, amt0, amt1, 0, 0, EXECUTE_SWAP_DEADLINE), caller=agent
        ).output
        return (liq, a0, a1)

    def remove_liquidity(
        self, token_id: int, percentage: float, agent: str
    ) -> Tuple[int, int]:
        """
        Remove a percentage amount of liquidity from the position.  This changes the caller's
        position and 'collects' and transfers tokens back to the caller.

        Args:
        - token ID for the position
        - percentage of liquidity to remove
        - agent: the caller address that's the owner of the position

        Returns:
        - Amount of token0 returned
        - Amount of token1 returned
        """
        assert percentage > 0 and percentage <= 1, "invalid percentage"

        _, _, _, _, _, _, _, liq, _, _, _, _ = self.nftposition.positions.call(token_id)
        amount = liq * percentage
        self.nftposition.decreaseLiquidity.transact(
            (token_id, int(amount), 0, 0, EXECUTE_SWAP_DEADLINE), caller=agent
        )

        # check position to see how much is owed to agent
        _, _, _, _, _, _, _, _, _, _, t0owed, t1owed = self.nftposition.positions.call(
            token_id
        )

        # call 'collect'
        result = self.nftposition.collect.transact(
            (token_id, agent, t0owed, t1owed), caller=agent
        )

        return result.output

    def swap_0_for_1(self, amount: float, agent: str):
        """
        Swap some 'amount' of token0 for token1.

        Args:
         - amount : the amount of token0 to use to buy token1
         - agent  : the agent's wallet address

        Returns:
        - amount of token0 spent
        - amount of token1 received

        NOTE:  Be sure the input amount is in the proper
        format for token0.  For example, if token0 is USDC, and you
        want to spend $3000 worth of USDC for token1, enter 3000. Under
        the covers, this method will offset for the actual decimal format.

        What does that mean?  USDC may have 18 decimal places, so the actual amount
        is 3000 * 1e18.  This method will convert to the configured decimal places.
        """
        b0, _ = self.pair_balance(agent)
        assert b0 >= amount, "insufficient balance!"
        amount_in = as_18(amount)

        # approve the router to move token's on behalf of the agent
        self.token0.approve.transact(self.router.address, amount_in, caller=agent)

        recv = self.router.exactInputSingle.transact(
            (
                self.token0.address,
                self.token1.address,
                self.fee,
                agent,
                EXECUTE_SWAP_DEADLINE,
                amount_in,
                0,
                0,
            ),
            caller=agent,
        )
        self.data.add_volume(amount_in, recv.output)
        return (amount_in, recv.output)

    def swap_1_for_0(self, amount, agent):
        """
        Swap some 'amount' of token1 for token0.

        Args:
         - amount : the amount of token0 to use to buy token1
         - agent  : the agent's wallet address

        Returns:
        - amount of token1 spent
        - amount of token0 received

        NOTE:  Be sure the input amount is in the proper
        format for token0.  For example, if token0 is USDC, and you
        want to spend $3000 worth of USDC for token1, enter 3000. Under
        the covers, this method will offset for the actual decimal format.

        What does that mean?  USDC may have 18 decimal places, so the actual amount
        is 3000 * 1e18.  This method will convert to the configured decimal places.
        """
        _, b1 = self.pair_balance(agent)
        assert b1 >= amount, "insufficient balance!"
        amount_in = as_18(amount)

        # approve the router to move token's on behalf of the agent
        self.token1.approve.transact(self.router.address, amount_in, caller=agent)

        recv = self.router.exactInputSingle.transact(
            (
                self.token1.address,
                self.token0.address,
                self.fee,
                agent,
                EXECUTE_SWAP_DEADLINE,
                amount_in,
                0,
                0,
            ),
            caller=agent,
        )

        self.data.add_volume(recv.output, amount_in)
        return (amount_in, recv.output)

    def collect_data(self, step: int):
        """
        Called in the model step after agents run
        """
        tick = self.pool_contract.slot0.call()[1]
        t0p, t1p = self.exchange_prices()
        r0, r1 = self.reserves()

        self.data.step.append(step)
        self.data.tick.append(tick)
        self.data.t0_price.append(t0p)
        self.data.t1_price.append(t1p)
        self.data.collect_volume()
        self.data.t0_reserves.append(r0)
        self.data.t1_reserves.append(r1)

    def dataframe(self):
        """
        Convert data into a dataframe
        """
        return self.data.into_dataframe()
