"""
This is a work in progress...  While it works, it will most likely evolve
as we develop models with it.
"""

from typing import List
from simular import PyEvm

from unisim.pool import Pool, Token
from unisim.abis import uniswap_router_contract, uniswap_nftpositionmanager


class DEX:
    """
    Uniswap exchange with 1 or more pools.  Use this class to setup and
    interact with pools in a model.
    """

    def __init__(self, evm: PyEvm):
        # Setup the EVM and needed Uniswap contracts
        self.__evm = evm
        self.__router = uniswap_router_contract(evm)
        self.__nft = uniswap_nftpositionmanager(evm)

    def __setattr__(self, name: str, value: Pool) -> None:
        # Use the internal dictionary to store a pool keyed by
        # the pool's name.  A pool's name is made up of the token
        # symbols and fee.  For example, if a pool contains the tokens
        # USDC and DAI and the fee is 500, the keyed name of the pool
        # would be: 'USDC_DAI_500'.  You can then access the pool as a
        # property of this class: dex.USDC_DAI_500....
        if self.__dict__.get(name):
            raise Exception(f"Duplicate Pool: '{name}' already exists")
        self.__dict__[name] = value

    def add_pool(self, t0: Token, t1: Token, fee: int, deployer: str) -> None:
        """
        Add a pool to the exchange.
        """
        p = Pool(self.__evm, t0, t1, fee, self.__router, self.__nft, deployer)
        self.__setattr__(p.name, p)

    def __filter_pools(self):
        # Since we're using the internal __dict__, there will be other stuff stored,
        # so we filter to have only the pools
        return [(k, v) for k, v in self.__dict__.items() if isinstance(v, Pool)]

    def list(self) -> List[str]:
        """
        List all pools
        """
        return [name for name, _ in self.__filter_pools()]

    def total_number_pools(self) -> int:
        """
        Return the number of pools in the exchange
        """
        return len(self.__filter_pools())

    def collect_data(self, step_num: int) -> None:
        """
        Loop through pools and collect data.  Called in the model 'step'
        """
        for _, pool in self.__filter_pools():
            pool.collect_data(step_num)
