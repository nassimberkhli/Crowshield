from contracts.simulation import build_trace_for_contract, run_batched_simulation
from contracts.utils import (
    CHECKPOINT_ROUND_1,
    CHECKPOINT_ROUND_2,
    CHECKPOINT_ROUND_3,
    CHECKPOINT_ROUND_4,
    INIT_BATCH_SIZE,
    SIM_BATCH_SIZE,
    TOTAL_BITS,
    TOTAL_ROUNDS,
)


def ask_int(prompt: str, minimum: int | None = None, maximum: int | None = None) -> int:
    while True:
        raw_value = input(prompt).strip()

        try:
            value = int(raw_value)
        except ValueError:
            print("[ERROR] Please enter a valid integer.")
            continue

        if minimum is not None and value < minimum:
            print(f"[ERROR] Please enter an integer greater than or equal to {minimum}.")
            continue

        if maximum is not None and value > maximum:
            print(f"[ERROR] Please enter an integer less than or equal to {maximum}.")
            continue

        return value


def main() -> None:
    print("=== Binary Automaton Manual Simulation ===")
    print("Project parameters are fixed by the code.")
    print(f"Total bits: {TOTAL_BITS}")
    print(f"Total rounds: {TOTAL_ROUNDS}")
    print(f"Initialization batch size: {INIT_BATCH_SIZE}")
    print(f"Simulation batch size: {SIM_BATCH_SIZE}")
    print(
        "Checkpoint rounds: "
        f"{CHECKPOINT_ROUND_1}, {CHECKPOINT_ROUND_2}, "
        f"{CHECKPOINT_ROUND_3}, {CHECKPOINT_ROUND_4}"
    )
    print()

    secret1 = ask_int(
        "Player 1 secret (0 to 2^128 - 1): ",
        minimum=0,
        maximum=(1 << 128) - 1,
    )
    secret2 = ask_int(
        "Player 2 secret (0 to 2^128 - 1): ",
        minimum=0,
        maximum=(1 << 128) - 1,
    )

    print()
    print("[INFO] Running manual simulation...")
    _, final_bit = run_batched_simulation(
        secret1=secret1,
        secret2=secret2,
        total_bits=TOTAL_BITS,
        total_rounds=TOTAL_ROUNDS,
        init_batch_size=INIT_BATCH_SIZE,
        sim_batch_size=SIM_BATCH_SIZE,
    )

    (
        traced_final_bit,
        checkpoint1,
        checkpoint2,
        checkpoint3,
        checkpoint4,
    ) = build_trace_for_contract(
        secret1=secret1,
        secret2=secret2,
        total_bits=TOTAL_BITS,
        total_rounds=TOTAL_ROUNDS,
        checkpoint_round_1=CHECKPOINT_ROUND_1,
        checkpoint_round_2=CHECKPOINT_ROUND_2,
        checkpoint_round_3=CHECKPOINT_ROUND_3,
        checkpoint_round_4=CHECKPOINT_ROUND_4,
    )

    print("[INFO] Simulation finished.")
    print()
    print("=== Version 1 ===")
    print("Agreement or disagreement is decided from the final bit and checkpoint hashes.")
    print(f"Final bit: {final_bit}")
    print()
    print("=== Version 2 ===")
    print("A dispute can narrow from mismatching checkpoints to a local Rule 150 step.")
    print(f"Traced final bit: {traced_final_bit}")
    print(f"Checkpoint 1 hash: {checkpoint1}")
    print(f"Checkpoint 2 hash: {checkpoint2}")
    print(f"Checkpoint 3 hash: {checkpoint3}")
    print(f"Checkpoint 4 hash: {checkpoint4}")
    print(f"Winner: {'player1' if final_bit == 0 else 'player2'}")


if __name__ == "__main__":
    main()
