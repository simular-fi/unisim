import mesa
from tqdm import tqdm

from unisim.pool import Pool, Token
from unisim.abis import uniswap_router_contract, uniswap_nftpositionmanager
from simular import create_account, create_many_accounts

from .agents import ZIAgent, LPAgent, PERCENTAGE_OF_LP_AGENTS

# random generator seed
SEED = 1234


class StablecoinModel(mesa.Model):
    def __init__(self, evm, num_agents, num_steps):
        super().__init__()

        self.num_agents = num_agents
        self.num_steps = num_steps
        self.random.seed(SEED)
        # randomly activate agents on each step
        # self.schedule = mesa.time.RandomActivation(self)

        # load needed contracts
        router = uniswap_router_contract(evm)
        nft = uniswap_nftpositionmanager(evm)

        # create the pool
        token0 = Token("DIA", 1)
        token1 = Token("USDC", 1)
        deployer = create_account(evm)
        self.pool = Pool(evm, token0, token1, 500, router, nft, deployer)

        id = 0
        # create the lp agents
        total_lp_agents = round(num_agents * PERCENTAGE_OF_LP_AGENTS)
        lpagents = create_many_accounts(evm, total_lp_agents)
        for lp_address in lpagents:
            self.agents.add(LPAgent(lp_address, self))
            id += 1

        # create the trader agents
        ziagents = create_many_accounts(evm, num_agents)
        for za in ziagents:
            # fund the agent
            self.agents.add(ZIAgent(za, self))
            id += 1

    def step(self):
        # self.schedule.step()
        self.agents.shuffle_do("step")
        self.pool.collect_data(self.steps)

    def run_model(self):
        for _ in tqdm(range(self.num_steps)):
            self.step()

    def results(self):
        return self.pool.dataframe()
