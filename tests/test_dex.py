from unisim.dex import DEX
from unisim.pool import Token


def test_dex_setup(snapshot_evm, deployer):
    dex = DEX(snapshot_evm)
    dex.add_pool(Token("USDC", 1), Token("DAI", 1), 500, deployer)
    dex.add_pool(Token("DAI", 2700.0), Token("ETH", 1), 500, deployer)

    assert "USDC" == dex.USDC_DAI_500.token0.symbol.call()
    assert "DAI" == dex.USDC_DAI_500.token1.symbol.call()

    assert 2 == dex.total_number_pools()
    assert ["USDC_DAI_500", "DAI_ETH_500"] == dex.list()
