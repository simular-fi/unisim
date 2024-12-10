import os
from simular import PyEvm, create_account

from unisim.abis import (
    uniswap_factory_contract,
    uniswap_nftpositionmanager,
    uniswap_router_contract,
)
from unisim.pool import FEE_RANGE

BASE_STATE = "./snapshots/base.json"


def base_uniswap_state():
    """
    Pull base contract state from a remote Ethereum node on mainchain.
    This doesn't pull all the state in each contract. It primarily focuses
    on contract bytecode which is what's needed to create a local instance
    of the contract in our modeling environment.
    """
    # TODO: change to a more generic env var
    alchemyurl = os.getenv("ALCHEMY")
    assert alchemyurl, "Missing ALCHEMY rpc node token key"

    # create vm that pulls from remote node
    evm = PyEvm.from_fork(url=alchemyurl)

    create_account(evm, address="0x1a9c8182c09f50c8318d769245bea52c32be35bc")

    # factory
    factory = uniswap_factory_contract(evm)
    for fee in FEE_RANGE:
        factory.feeAmountTickSpacing.call(fee)
    factory.owner.call()

    # router
    router = uniswap_router_contract(evm)
    router.factory.call()
    router.WETH9.call()

    # nft
    nft = uniswap_nftpositionmanager(evm)
    nft.factory.call()
    nft.WETH9.call()

    print(" ... saving base state ...")
    snap = evm.create_snapshot()
    with open(f"{BASE_STATE}", "w") as f:
        f.write(snap)
