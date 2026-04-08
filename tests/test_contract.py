import smartpy as sp

from contracts.contract import bet_contract
from contracts.simulation import run_batched_simulation
from contracts.utils import (
    JOIN_WINDOW_SECONDS,
    PROGRESS_WINDOW_SECONDS,
    REVEAL_WINDOW_SECONDS,
)
from utils.logs import info, section, success


TEST_TOTAL_BITS = 16
TEST_TOTAL_ROUNDS = 8
TEST_INIT_BATCH_SIZE = 4
TEST_SIM_BATCH_SIZE = 8


def make_commitment(player_address, secret, salt):
    payload = sp.record(player=player_address, secret=secret, salt=salt)
    return sp.blake2b(sp.pack(payload))


@sp.add_test()
def test_happy_path_batched_game():
    section("Smart contract happy-path test")
    info("Creating SmartPy scenario for a complete and aligned game flow.")

    scenario = sp.test_scenario()

    alice = sp.test_account("alice")
    bob = sp.test_account("bob")

    contract = bet_contract.BinaryAutomatonBet(
        JOIN_WINDOW_SECONDS,
        REVEAL_WINDOW_SECONDS,
        PROGRESS_WINDOW_SECONDS,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_INIT_BATCH_SIZE,
        TEST_SIM_BATCH_SIZE,
    )
    scenario += contract

    alice_secret = 42
    bob_secret = 99
    alice_salt = sp.bytes("0x11111111111111111111111111111111")
    bob_salt = sp.bytes("0x22222222222222222222222222222222")

    info("Building commitments for both players.")
    alice_commitment = make_commitment(alice.address, alice_secret, alice_salt)
    bob_commitment = make_commitment(bob.address, bob_secret, bob_salt)

    info("Joining both players with the required 10 tez stake.")
    contract.join(
        alice_commitment,
        _sender=alice,
        _amount=sp.tez(10),
        _now=sp.timestamp(0),
    )
    contract.join(
        bob_commitment,
        _sender=bob,
        _amount=sp.tez(10),
        _now=sp.timestamp(1),
    )

    info("Revealing both secrets within the reveal window.")
    contract.reveal(
        sp.record(secret=alice_secret, salt=alice_salt),
        _sender=alice,
        _now=sp.timestamp(2),
    )
    contract.reveal(
        sp.record(secret=bob_secret, salt=bob_salt),
        _sender=bob,
        _now=sp.timestamp(3),
    )

    info("Running initialization batches.")
    total_init_calls = (TEST_TOTAL_BITS + TEST_INIT_BATCH_SIZE - 1) // TEST_INIT_BATCH_SIZE
    for step in range(total_init_calls):
        contract.initialize_batch(
            _sender=alice,
            _now=sp.timestamp(10 + step),
        )

    info("Running simulation batches.")
    total_simulation_calls = (
        TEST_TOTAL_BITS * TEST_TOTAL_ROUNDS + TEST_SIM_BATCH_SIZE - 1
    ) // TEST_SIM_BATCH_SIZE
    for step in range(total_simulation_calls):
        contract.simulate_batch(
            _sender=bob,
            _now=sp.timestamp(100 + step),
        )

    info("Comparing the on-chain result with the Python reference simulation.")
    _, expected = run_batched_simulation(
        alice_secret,
        bob_secret,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_INIT_BATCH_SIZE,
        TEST_SIM_BATCH_SIZE,
    )
    expected_winner = alice.address if expected == 0 else bob.address

    scenario.verify(contract.data.finished)
    scenario.verify(contract.data.outcome_bit.unwrap_some() == expected)
    scenario.verify(contract.data.winner.unwrap_some() == expected_winner)
    scenario.verify(contract.balance == sp.tez(0))

    success("Happy-path SmartPy test completed successfully.")


@sp.add_test()
def test_timeout_refund_before_second_player():
    section("Smart contract join-timeout test")
    info("Creating SmartPy scenario for the single-player timeout refund case.")

    scenario = sp.test_scenario()
    alice = sp.test_account("alice")

    contract = bet_contract.BinaryAutomatonBet(
        10,
        REVEAL_WINDOW_SECONDS,
        PROGRESS_WINDOW_SECONDS,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_INIT_BATCH_SIZE,
        TEST_SIM_BATCH_SIZE,
    )
    scenario += contract

    secret = 5
    salt = sp.bytes("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    commitment = make_commitment(alice.address, secret, salt)

    contract.join(
        commitment,
        _sender=alice,
        _amount=sp.tez(10),
        _now=sp.timestamp(0),
    )

    contract.claim_timeout(
        _sender=alice,
        _now=sp.timestamp(11),
    )

    scenario.verify(contract.data.finished)
    scenario.verify(contract.data.winner.unwrap_some() == alice.address)
    scenario.verify(contract.balance == sp.tez(0))

    success("Single-player timeout refund test completed successfully.")


if __name__ == "__main__":
    success("test_contract.py executed. SmartPy registered the contract test scenarios.")
