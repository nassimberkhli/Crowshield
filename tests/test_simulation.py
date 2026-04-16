from contracts.simulation import (
    build_initial_state,
    build_trace_for_contract,
    hash_state,
    run_batched_simulation,
    run_full_simulation,
    run_full_simulation_with_checkpoints,
    step_rule150_ring,
)
from utils.logs import info, section, success


def test_initial_state_is_deterministic_concatenation():
    section("Simulation test suite")
    info(
        "Checking that the initial state is a deterministic concatenation of both secrets."
    )

    secret1 = 0b1011
    secret2 = 0b0110
    state = build_initial_state(secret1, secret2, 8)

    assert state == [1, 1, 0, 1, 0, 1, 1, 0]
    success(
        "Initial state generation is deterministic and matches the concatenation rule."
    )


def test_rule150_uses_left_center_and_right():
    info("Checking that the automaton rule depends on left, center, and right cells.")

    state = [1, 0, 1, 1, 0]
    next_state = step_rule150_ring(state)

    assert next_state == [1, 0, 0, 0, 0]
    success("The automaton rule correctly uses left, center, and right neighbors.")


def test_reference_equivalence():
    info("Checking equivalence between full simulation and batched simulation.")

    cases = [
        (0, 0, 8, 4, 2, 2),
        (1, 0, 8, 5, 3, 2),
        (7, 9, 16, 8, 4, 4),
        (42, 1337, 32, 12, 5, 7),
        (123456789, 987654321, 64, 16, 8, 8),
        (123456789, 987654321, 512, 16, 8, 8),
    ]

    for index, (
        secret1,
        secret2,
        total_bits,
        total_rounds,
        init_batch_size,
        sim_batch_size,
    ) in enumerate(cases, start=1):
        info(
            f"Case {index}: secret1={secret1}, secret2={secret2}, "
            f"total_bits={total_bits}, total_rounds={total_rounds}, "
            f"init_batch_size={init_batch_size}, sim_batch_size={sim_batch_size}"
        )

        full_state, full_bit = run_full_simulation(
            secret1,
            secret2,
            total_bits,
            total_rounds,
        )
        batched_state, batched_bit = run_batched_simulation(
            secret1,
            secret2,
            total_bits,
            total_rounds,
            init_batch_size,
            sim_batch_size,
        )

        assert full_state == batched_state
        assert full_bit == batched_bit

    success("Full simulation and batched simulation are equivalent for all cases.")


def test_initial_state_reuses_128_secret_bits():
    info(
        "Checking that initial state reuses secret bits when total_bits is greater than 128."
    )

    secret1 = 0b1011
    secret2 = 0b0110
    state = build_initial_state(secret1, secret2, 512)

    assert len(state) == 512

    assert state[0] == state[128]
    assert state[1] == state[129]
    assert state[2] == state[130]
    assert state[3] == state[131]

    assert state[256] == state[384]
    assert state[257] == state[385]
    assert state[258] == state[386]
    assert state[259] == state[387]

    success("Initial state reuses the 128 secret bits correctly.")


def test_output_is_binary():
    info("Checking that the simulation output is strictly binary.")
    _, bit = run_batched_simulation(5, 6, 16, 8, 4, 4)
    assert bit in (0, 1)
    success("Simulation output is binary.")


def test_checkpoint_hashes_are_generated():
    info("Checking that checkpoint hashes are produced for the requested rounds.")
    _, bit, checkpoint_states, checkpoint_hashes = run_full_simulation_with_checkpoints(
        secret1=5,
        secret2=6,
        total_bits=16,
        total_rounds=8,
        checkpoint_rounds=[2, 4, 6, 7],
    )

    assert bit in (0, 1)
    assert sorted(checkpoint_states.keys()) == [2, 4, 6, 7]
    assert sorted(checkpoint_hashes.keys()) == [2, 4, 6, 7]
    assert checkpoint_hashes[2] == hash_state(checkpoint_states[2])
    assert checkpoint_hashes[4] == hash_state(checkpoint_states[4])

    success("Checkpoint hashes are generated correctly.")


def test_trace_builder_returns_contract_order():
    info("Checking that the trace builder returns the final bit and four checkpoint hashes.")

    final_bit, checkpoint1, checkpoint2, checkpoint3, checkpoint4 = build_trace_for_contract(
        secret1=12,
        secret2=34,
        total_bits=16,
        total_rounds=8,
        checkpoint_round_1=2,
        checkpoint_round_2=4,
        checkpoint_round_3=6,
        checkpoint_round_4=7,
    )

    assert final_bit in (0, 1)
    assert checkpoint1.startswith("0x")
    assert checkpoint2.startswith("0x")
    assert checkpoint3.startswith("0x")
    assert checkpoint4.startswith("0x")

    success("Trace builder returns data in the contract reveal order.")


if __name__ == "__main__":
    test_initial_state_is_deterministic_concatenation()
    test_rule150_uses_left_center_and_right()
    test_reference_equivalence()
    test_initial_state_reuses_128_secret_bits()
    test_output_is_binary()
    test_checkpoint_hashes_are_generated()
    test_trace_builder_returns_contract_order()
    success("test_simulation.py completed successfully.")
