import hashlib

from contracts.utils import SECRET_BITS


def commitment_payload(player_address, secret, salt):
    return {"player": player_address, "secret": secret, "salt": salt}


def trace_commitment_payload(
    player_address,
    final_bit,
    checkpoint1,
    checkpoint2,
    checkpoint3,
    checkpoint4,
    salt,
):
    return {
        "player": player_address,
        "final_bit": final_bit,
        "checkpoint1": checkpoint1,
        "checkpoint2": checkpoint2,
        "checkpoint3": checkpoint3,
        "checkpoint4": checkpoint4,
        "salt": salt,
    }


def extract_bit(value: int, shift: int) -> int:
    return (value >> shift) & 1


def reduce_shift_128(value: int) -> int:
    return value % SECRET_BITS


def initial_bit(secret1: int, secret2: int, index: int, total_bits: int) -> int:
    half_bits = total_bits // 2

    if index < half_bits:
        return extract_bit(secret1, reduce_shift_128(index))

    return extract_bit(secret2, reduce_shift_128(index - half_bits))


def build_initial_state(secret1: int, secret2: int, total_bits: int) -> list[int]:
    if total_bits <= 0 or total_bits % 2 != 0:
        raise ValueError("total_bits must be a positive even integer")

    return [initial_bit(secret1, secret2, i, total_bits) for i in range(total_bits)]


def step_rule150_ring(state: list[int]) -> list[int]:
    n = len(state)
    out = [0] * n

    for i in range(n):
        out[i] = state[(i - 1) % n] ^ state[i] ^ state[(i + 1) % n]

    return out


def final_result_bit(state: list[int]) -> int:
    center_index = len(state) // 2
    return state[center_index]


def state_to_hex(state: list[int]) -> str:
    return "0x" + "".join(str(bit) for bit in state)


def hash_state(state: list[int]) -> str:
    payload = "".join(str(bit) for bit in state).encode()
    return "0x" + hashlib.blake2b(payload, digest_size=32).hexdigest()


def run_full_simulation(
    secret1: int,
    secret2: int,
    total_bits: int,
    total_rounds: int,
) -> tuple[list[int], int]:
    state = build_initial_state(secret1, secret2, total_bits)

    for _ in range(total_rounds):
        state = step_rule150_ring(state)

    return state, final_result_bit(state)


def run_batched_simulation(
    secret1: int,
    secret2: int,
    total_bits: int,
    total_rounds: int,
    init_batch_size: int,
    sim_batch_size: int,
) -> tuple[list[int], int]:
    if init_batch_size <= 0:
        raise ValueError("init_batch_size must be positive")

    if sim_batch_size <= 0:
        raise ValueError("sim_batch_size must be positive")

    state0 = [0] * total_bits
    state1 = [0] * total_bits

    init_cursor = 0
    while init_cursor < total_bits:
        for _ in range(init_batch_size):
            if init_cursor < total_bits:
                state0[init_cursor] = initial_bit(
                    secret1, secret2, init_cursor, total_bits
                )
                init_cursor += 1

    active = 0
    current_round = 0
    current_index = 0

    while current_round < total_rounds:
        for _ in range(sim_batch_size):
            if current_round < total_rounds:
                src = state0 if active == 0 else state1
                dst = state1 if active == 0 else state0

                left_index = total_bits - 1 if current_index == 0 else current_index - 1
                right_index = 0 if current_index + 1 == total_bits else current_index + 1

                dst[current_index] = (
                    src[left_index] ^ src[current_index] ^ src[right_index]
                )
                current_index += 1

                if current_index == total_bits:
                    current_index = 0
                    current_round += 1
                    active = 1 - active

    final_state = state0 if active == 0 else state1
    return final_state, final_result_bit(final_state)


def run_full_simulation_with_checkpoints(
    secret1: int,
    secret2: int,
    total_bits: int,
    total_rounds: int,
    checkpoint_rounds: list[int],
) -> tuple[list[int], int, dict[int, list[int]], dict[int, str]]:
    state = build_initial_state(secret1, secret2, total_bits)
    checkpoints_states: dict[int, list[int]] = {}
    checkpoints_hashes: dict[int, str] = {}

    for current_round in range(1, total_rounds + 1):
        state = step_rule150_ring(state)

        if current_round in checkpoint_rounds:
            checkpoints_states[current_round] = list(state)
            checkpoints_hashes[current_round] = hash_state(state)

    return state, final_result_bit(state), checkpoints_states, checkpoints_hashes


def build_trace_for_contract(
    secret1: int,
    secret2: int,
    total_bits: int,
    total_rounds: int,
    checkpoint_round_1: int,
    checkpoint_round_2: int,
    checkpoint_round_3: int,
    checkpoint_round_4: int,
) -> tuple[int, str, str, str, str]:
    checkpoint_rounds = [
        checkpoint_round_1,
        checkpoint_round_2,
        checkpoint_round_3,
        checkpoint_round_4,
    ]
    _, final_bit, _, checkpoint_hashes = run_full_simulation_with_checkpoints(
        secret1=secret1,
        secret2=secret2,
        total_bits=total_bits,
        total_rounds=total_rounds,
        checkpoint_rounds=checkpoint_rounds,
    )

    return (
        final_bit,
        checkpoint_hashes[checkpoint_round_1],
        checkpoint_hashes[checkpoint_round_2],
        checkpoint_hashes[checkpoint_round_3],
        checkpoint_hashes[checkpoint_round_4],
    )
