from unisim.abis import (
    uniswap_nftpositionmanager,
    uniswap_router_contract,
)
from unisim.pool import Pool, Token


def test_decrease_liquidity(snapshot_evm, deployer):
    fee = 500
    router = uniswap_router_contract(snapshot_evm)
    nft = uniswap_nftpositionmanager(snapshot_evm)
    ta = Token("USDC", 3300)
    tb = Token("WETH", 1)

    pool = Pool(snapshot_evm, ta, tb, fee, router, nft, deployer)
    pool.mint_tokens(9900, 3, deployer)
    assert (0, 0) == pool.reserves()
    _, _, tokenid = pool.mint_position(3300, 1, 3200, 3400, deployer)

    r0, r1 = pool.reserves()
    _, _, _, liqA = pool.get_position(tokenid)
    assert r0 == 3300.0
    assert r1 == 0.9945346429884085

    pool.remove_liquidity(tokenid, 0.5, deployer)

    r0a, r1a = pool.reserves()
    _, _, _, liqB = pool.get_position(tokenid)
    assert r0a == 1650.0
    assert r1a == 0.4972673214942043
    assert liqB < liqA


def test_increase_liquidity(snapshot_evm, deployer):
    fee = 500
    router = uniswap_router_contract(snapshot_evm)
    nft = uniswap_nftpositionmanager(snapshot_evm)
    ta = Token("USDC", 1)
    tb = Token("DAI", 1)
    pool = Pool(snapshot_evm, ta, tb, fee, router, nft, deployer)

    pool.mint_tokens(100, 100, deployer)

    # create initial position
    _, _, tokenid = pool.mint_position(50, 50, 0.99, 1.01, deployer)
    assert (50, 50) == pool.reserves()
    _, _, _, liq0 = pool.get_position(tokenid)

    # increase position
    pool.increase_liquidity(tokenid, 10, 10, deployer)

    _, _, _, liq1 = pool.get_position(tokenid)
    assert liq1 > liq0
    assert (60, 60) == pool.reserves()
