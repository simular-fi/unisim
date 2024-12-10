import pytest
from simular import PyEvm, create_account


"""
Fixtures
"""


@pytest.fixture
def snapshot_evm():
    with open("./snapshots/base.json") as b:
        state = b.read()
    return PyEvm.from_snapshot(state)


@pytest.fixture
def deployer(snapshot_evm):
    return create_account(snapshot_evm, value=int(1000e18))
