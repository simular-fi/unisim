# Stablecoin Trading

## Pool
- `DIA/USDC` token pair. Both are stablecoins
- Initial liquidity: $10,000,000 concentrated in the range: $0.98 - $1.03
- Fee: 500 bps

## Agent
- Random activation of agents
- Zero Intelligence
  - configurable probability they will trade
  - random selection of the token to trade
  - randomized amount to trade in the range: $5 - $100
- Initial funding $10,000 per token

## Run time stats:
- `10,000` agents
- `500` steps
- `~1.45` steps per second
- Total runtime: `~5 mins 46 seconds`
- Results captured to a dataframe store in: `base_10000_500.avro`

Overall, the pool stays relatively stable across the run.  This is most likely due
to the amount of liquidity concentrated in a small range, and the low trade amount among agents. See the [Jupyter notebook](usdc_dia.ipynb) for results of the data.
