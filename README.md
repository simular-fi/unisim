# Unisim: Modeling Uniswap 3

A simple library to create Uniswap pools for agent-based modeling or other experimentation. This code makes it easy to configure and deploy a number of token pools for trading.

See the `example` folder and `tests`.

## Install

Not current available on PyPi.  You can install with pip via Github:

```console
> pip install unisim@git+https://github.com/davebryson/unisim
```


## Setup 
The project uses [hatch](https://hatch.pypa.io/latest/install/) to manage the virtual environment. Hatch is not required.  But, it's highly recommended to use a python virtual environment.  If you want to use hatch:

[How to install hatch](https://hatch.pypa.io/latest/install/)

Once `hatch` is installed, from within this directory run:

```console
> hatch shell
```
This switches to the local virtual environment.  The first time you run the command all the dependencies in `pyproject.toml` will be installed.  Additionally, anytime you add deps
they will be auto-installed when switching into the virtual environment.

To run the example:

```console
> python main.py
```

## Other stuff

The project's dependencies include `jupyter` for the notebooks in the project.  You start it in this directory by running:

```console
> jupyter lab
```

## Pools

A pool is made up of a pair of tokens that can be exchanged.   Each token is configured with a symbol name and initial exchange price.

### Creating a pool

Required imports:
```python
# Required contracts
from unisim.abis import (
    uniswap_factory_contract,
    uniswap_nftpositionmanager,
    uniswap_router_contract,
)
# pool and token API
from unisim.pool import Pool, Token
```

Creating the EVM:
```python
# Load all the contract from the snapshot
with open("./snapshots/base.json") as b:
    state = b.read()
    evm = PyEvm.from_snapshot(state)
```

Setup required contracts with the EVM:

```python
factory = uniswap_factory_contract(evm)
router = uniswap_router_contract(evm)
nft = uniswap_nftpositionmanager(evm)
```

Configure the tokens:
```python
# Set the fee for the pool
fee = 500

# Setup each token with a symbol name and price.
# note the price is in $.  Token1 is usually always 1. 
# In this example the exchange rate is 1 WETH == 3300 USDC
token0 = Token("USDC", 3300)
token1 = Token("WETH", 1)
```

Finally create the pool:
```python
pool = Pool(evm, token0, token1, fee, router, nft, deployer)
```
You can now use the pool API to perform almost all functions on the exchange:
swap, add/remove liquidity, and more.  See *example* and *tests*.
