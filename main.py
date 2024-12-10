"""
CLI to run the example model.
"""

import argparse

from simular import PyEvm
from example.model import StablecoinModel


def run(nagent, nsteps, save=False):
    with open("./snapshots/base.json") as b:
        state = b.read()
    evm = PyEvm.from_snapshot(state)
    model = StablecoinModel(evm, nagent, nsteps)

    print(
        f""" 
            ... running the model with {NUM_AGENTS} agents for {NUM_STEPS} steps ...
        """
    )

    model.run_model()
    df = model.results()
    print(df)

    if save:
        output_fn = f"example/dia_usdc_{nagent}_{nsteps}.avro"
        df.write_avro(output_fn)
        print(f" ... saved dataframe to: {output_fn} ...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py")
    parser.add_argument(
        "--nagents", default=100, help="Set number of agents (default 100)"
    )
    parser.add_argument("--nsteps", default=50, help="Set number of steps (default 20)")
    parser.add_argument(
        "--save",
        action="store_true",
        help="If set, will save model output dataframe to file",
    )

    args = parser.parse_args()

    NUM_AGENTS = int(args.nagents)
    NUM_STEPS = int(args.nsteps)

    run(NUM_AGENTS, NUM_STEPS, args.save)
