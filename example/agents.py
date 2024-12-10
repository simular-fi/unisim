import mesa

####
# *** ZI AGENT SETTINGS ***
# initial funding
ZI_AGENT_FUNDING = 10_000
# probability they'll do some trading
SWAP_PROB = 0.8
# range amount to trade
RAND_RANGE = (5, 100)
####

####
# *** LP AGENT SETTINGS ***

# the number of LPs compared to total model agents
PERCENTAGE_OF_LP_AGENTS = 0.1
# initial balance for each token in the pool
INITIAL_TOKEN_BALANCE = 10_000
# initial liquidity position
INITIAL_POSITION_AMOUNT = 1000
# range amount they may increase the pool by
POSITION_RANGE = (500, 1_000)
# stable coint position ranges
PRICE_RANGE = [
    (0.98, 1.0),
    (0.985, 1.01),
    (0.99, 1.03),
]
####


class ZIAgent(mesa.Agent):
    """
    I'm the ZI trader. I might not be the sharpest tool in the shed,
    but luck has always been on my side.  Let's give this crypto stuff a try...
    """

    def __init__(self, address, model):
        super().__init__(model)
        self.address = address
        self.model = model
        self.model.pool.mint_tokens(ZI_AGENT_FUNDING, ZI_AGENT_FUNDING, address)

    def step(self):
        if self.model.random.random() < SWAP_PROB:
            token_to_buy = self.model.random.choice([0, 1])
            random_amount = self.model.random.randrange(RAND_RANGE[0], RAND_RANGE[1])
            if token_to_buy == 0:
                self.model.pool.swap_1_for_0(random_amount, self.address)
            else:
                self.model.pool.swap_0_for_1(random_amount, self.address)


class LPAgent(mesa.Agent):
    """
    The LP'er.  Without me, there's nothing to trade...

    Add / Remove pool liquidity
    Each agent starts with a single, random position.
    On step, the agent may increase or decrease their position.
    """

    def __init__(self, address, model):
        super().__init__(model)
        self.address = address
        self.model = model
        # mint tokens
        self.model.pool.mint_tokens(
            INITIAL_TOKEN_BALANCE, INITIAL_TOKEN_BALANCE, self.address
        )
        # mint position
        lp_position = self.model.random.choice(PRICE_RANGE)
        _, _, self.tokenid = self.model.pool.mint_position(
            INITIAL_POSITION_AMOUNT,
            INITIAL_POSITION_AMOUNT,
            lp_position[0],
            lp_position[1],
            self.address,
        )

    def step(self):
        """
        increase, decrease liquidity or do nothing
        """
        # random choice:
        # 0 = do nothing
        # 1 = increase
        # 2 = decrese
        choice = self.model.random.choice([0, 1, 2])
        if choice == 0:
            return

        if choice == 1:
            # increase
            self.increase_liquidity()
        else:
            # decrease
            self.decrease_liquidity()

    def increase_liquidity(self):
        # select amount to add
        amount = self.model.random.randrange(POSITION_RANGE[0], POSITION_RANGE[1])
        # check balance to make sure we have enough
        x, y = self.model.pool.pair_balance(self.address)
        if amount <= x and amount <= y:
            # add liquidity
            self.model.pool.increase_liquidity(
                self.tokenid, amount, amount, self.address
            )

    def decrease_liquidity(self):
        # randomly remove a percentage of an agents position
        _, _, _, liquidity = self.model.pool.get_position(self.tokenid)
        if liquidity == 0:
            # nothing to remove...
            return
        # select from 5-20%
        percentage = self.model.random.randrange(5, 20) / 100
        self.model.pool.remove_liquidity(self.tokenid, percentage, self.address)


class WhaleAgent(mesa.Agent):
    """
    The great manipulator

    Dump a large amount of token0 for token1 over a consecutive number of steps.

    Reality check...this only significantly moves the price if the swap amount
    get close to pool reserves.
    """

    def __init__(self, address, model):
        super().__init__(model)
        self.address = address
        self.model = model
        # just hardcoded for now...experimenting
        self.whale_amount = 1_000_000
        self.activation_range = [50, 51, 52, 53]

        assert self.model.nsteps >= 53, "not enough steps for the current whale"

    def step(self):
        if self.model.schedule.steps in self.activation_range:
            self.model.pool.swap_0_for_1(self.whale_amount, self.address)


class BurnItAgent(mesa.Agent):
    """
    Run for the hills.

    This agent burns tokens.  Which means, they're cashing out to fiat.
    This will deplete token reserves IFF the agent has an LP position
    """

    def __init__(self, address, model):
        super().__init__(model)
        self.address = address
        self.model = model

    def step(self):
        # todo
        pass


class FomoAgent(mesa.Agent):
    """
    I follow the crowd. Volume is the key to success. When it increases, I jump in.
    """

    def __init__(self, address, model):
        super().__init__(model)
        self.address = address
        self.model = model

    def step(self):
        # todo
        pass
