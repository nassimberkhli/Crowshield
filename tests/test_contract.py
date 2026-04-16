import smartpy as sp

from contracts.contract import bet_contract
from contracts.simulation import build_trace_for_contract
from contracts.utils import (
    CHECKPOINT_ROUND_1,
    CHECKPOINT_ROUND_2,
    CHECKPOINT_ROUND_3,
    CHECKPOINT_ROUND_4,
    JOIN_WINDOW_SECONDS,
    PROGRESS_WINDOW_SECONDS,
    REVEAL_WINDOW_SECONDS,
)
from utils.logs import info, section, success


TEST_TOTAL_BITS = 16
TEST_TOTAL_ROUNDS = 8
TEST_INIT_BATCH_SIZE = 4
TEST_SIM_BATCH_SIZE = 8
TEST_CHECKPOINT_ROUND_1 = 2
TEST_CHECKPOINT_ROUND_2 = 4
TEST_CHECKPOINT_ROUND_3 = 6
TEST_CHECKPOINT_ROUND_4 = 7


def make_commitment(player_address, secret, salt):
    payload = sp.record(player=player_address, secret=secret, salt=salt)
    return sp.blake2b(sp.pack(payload))


def make_trace_commitment(
    player_address,
    final_bit,
    checkpoint1,
    checkpoint2,
    checkpoint3,
    checkpoint4,
    salt,
):
    payload = sp.record(
        player=player_address,
        final_bit=final_bit,
        checkpoint1=checkpoint1,
        checkpoint2=checkpoint2,
        checkpoint3=checkpoint3,
        checkpoint4=checkpoint4,
        salt=salt,
    )
    return sp.blake2b(sp.pack(payload))


@sp.add_test()
def test_happy_path_trace_agreement():
    section("Trace agreement happy path")
    info("Creating a scenario where both players reveal the same trace.")

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
        TEST_CHECKPOINT_ROUND_1,
        TEST_CHECKPOINT_ROUND_2,
        TEST_CHECKPOINT_ROUND_3,
        TEST_CHECKPOINT_ROUND_4,
    )
    scenario += contract

    alice_secret = 42
    bob_secret = 99
    alice_salt = sp.bytes("0x11111111111111111111111111111111")
    bob_salt = sp.bytes("0x22222222222222222222222222222222")
    alice_trace_salt = sp.bytes("0x33333333333333333333333333333333")
    bob_trace_salt = sp.bytes("0x44444444444444444444444444444444")

    alice_commitment = make_commitment(alice.address, alice_secret, alice_salt)
    bob_commitment = make_commitment(bob.address, bob_secret, bob_salt)

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

    (
        expected_bit,
        checkpoint1,
        checkpoint2,
        checkpoint3,
        checkpoint4,
    ) = build_trace_for_contract(
        alice_secret,
        bob_secret,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_CHECKPOINT_ROUND_1,
        TEST_CHECKPOINT_ROUND_2,
        TEST_CHECKPOINT_ROUND_3,
        TEST_CHECKPOINT_ROUND_4,
    )

    alice_trace_commitment = make_trace_commitment(
        alice.address,
        expected_bit,
        sp.bytes(checkpoint1),
        sp.bytes(checkpoint2),
        sp.bytes(checkpoint3),
        sp.bytes(checkpoint4),
        alice_trace_salt,
    )
    bob_trace_commitment = make_trace_commitment(
        bob.address,
        expected_bit,
        sp.bytes(checkpoint1),
        sp.bytes(checkpoint2),
        sp.bytes(checkpoint3),
        sp.bytes(checkpoint4),
        bob_trace_salt,
    )

    contract.commit_trace(
        alice_trace_commitment,
        _sender=alice,
        _now=sp.timestamp(10),
    )
    contract.commit_trace(
        bob_trace_commitment,
        _sender=bob,
        _now=sp.timestamp(11),
    )

    contract.reveal_trace(
        sp.record(
            final_bit=expected_bit,
            checkpoint1=sp.bytes(checkpoint1),
            checkpoint2=sp.bytes(checkpoint2),
            checkpoint3=sp.bytes(checkpoint3),
            checkpoint4=sp.bytes(checkpoint4),
            salt=alice_trace_salt,
        ),
        _sender=alice,
        _now=sp.timestamp(12),
    )
    contract.reveal_trace(
        sp.record(
            final_bit=expected_bit,
            checkpoint1=sp.bytes(checkpoint1),
            checkpoint2=sp.bytes(checkpoint2),
            checkpoint3=sp.bytes(checkpoint3),
            checkpoint4=sp.bytes(checkpoint4),
            salt=bob_trace_salt,
        ),
        _sender=bob,
        _now=sp.timestamp(13),
    )

    scenario.verify(contract.data.finished)
    scenario.verify(contract.data.phase == sp.nat(5))
    scenario.verify(contract.data.outcome_bit.unwrap_some() == expected_bit)

    if expected_bit == 0:
        scenario.verify(contract.data.winner.unwrap_some() == alice.address)
        scenario.verify(contract.data.player1_credit == sp.nat(20))
        contract.claim(_sender=alice, _now=sp.timestamp(20))
    else:
        scenario.verify(contract.data.winner.unwrap_some() == bob.address)
        scenario.verify(contract.data.player2_credit == sp.nat(20))
        contract.claim(_sender=bob, _now=sp.timestamp(20))

    scenario.verify(contract.balance == sp.tez(0))
    success("Trace agreement happy path completed successfully.")


@sp.add_test()
def test_v1_dispute_flag_then_timeout_forfeit():
    section("Version 1 dispute flag and timeout")
    info("Creating a scenario where disagreement enters dispute and timeout awards the active player.")

    scenario = sp.test_scenario()

    alice = sp.test_account("alice")
    bob = sp.test_account("bob")

    contract = bet_contract.BinaryAutomatonBet(
        JOIN_WINDOW_SECONDS,
        REVEAL_WINDOW_SECONDS,
        10,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_INIT_BATCH_SIZE,
        TEST_SIM_BATCH_SIZE,
        TEST_CHECKPOINT_ROUND_1,
        TEST_CHECKPOINT_ROUND_2,
        TEST_CHECKPOINT_ROUND_3,
        TEST_CHECKPOINT_ROUND_4,
    )
    scenario += contract

    alice_secret = 12
    bob_secret = 34
    alice_salt = sp.bytes("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    bob_salt = sp.bytes("0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    alice_trace_salt = sp.bytes("0xcccccccccccccccccccccccccccccccc")
    bob_trace_salt = sp.bytes("0xdddddddddddddddddddddddddddddddd")

    contract.join(
        make_commitment(alice.address, alice_secret, alice_salt),
        _sender=alice,
        _amount=sp.tez(10),
        _now=sp.timestamp(0),
    )
    contract.join(
        make_commitment(bob.address, bob_secret, bob_salt),
        _sender=bob,
        _amount=sp.tez(10),
        _now=sp.timestamp(1),
    )

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

    (
        expected_bit,
        checkpoint1,
        checkpoint2,
        checkpoint3,
        checkpoint4,
    ) = build_trace_for_contract(
        alice_secret,
        bob_secret,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_CHECKPOINT_ROUND_1,
        TEST_CHECKPOINT_ROUND_2,
        TEST_CHECKPOINT_ROUND_3,
        TEST_CHECKPOINT_ROUND_4,
    )

    alice_trace_commitment = make_trace_commitment(
        alice.address,
        expected_bit,
        sp.bytes(checkpoint1),
        sp.bytes(checkpoint2),
        sp.bytes(checkpoint3),
        sp.bytes(checkpoint4),
        alice_trace_salt,
    )
    bob_trace_commitment = make_trace_commitment(
        bob.address,
        1 - expected_bit,
        sp.bytes("0x01"),
        sp.bytes(checkpoint2),
        sp.bytes(checkpoint3),
        sp.bytes(checkpoint4),
        bob_trace_salt,
    )

    contract.commit_trace(
        alice_trace_commitment,
        _sender=alice,
        _now=sp.timestamp(4),
    )
    contract.commit_trace(
        bob_trace_commitment,
        _sender=bob,
        _now=sp.timestamp(5),
    )

    contract.reveal_trace(
        sp.record(
            final_bit=expected_bit,
            checkpoint1=sp.bytes(checkpoint1),
            checkpoint2=sp.bytes(checkpoint2),
            checkpoint3=sp.bytes(checkpoint3),
            checkpoint4=sp.bytes(checkpoint4),
            salt=alice_trace_salt,
        ),
        _sender=alice,
        _now=sp.timestamp(6),
    )
    contract.reveal_trace(
        sp.record(
            final_bit=1 - expected_bit,
            checkpoint1=sp.bytes("0x01"),
            checkpoint2=sp.bytes(checkpoint2),
            checkpoint3=sp.bytes(checkpoint3),
            checkpoint4=sp.bytes(checkpoint4),
            salt=bob_trace_salt,
        ),
        _sender=bob,
        _now=sp.timestamp(7),
    )

    scenario.verify(contract.data.phase == sp.nat(4))

    contract.open_dispute(
        _sender=alice,
        _now=sp.timestamp(8),
    )
    contract.submit_checkpoint(
        sp.record(
            round_index=sp.nat(TEST_CHECKPOINT_ROUND_1),
            state_hash=sp.bytes(checkpoint1),
            proof=sp.bytes("0xaaaa"),
        ),
        _sender=alice,
        _now=sp.timestamp(9),
    )

    contract.claim_timeout(
        _sender=alice,
        _now=sp.timestamp(20),
    )

    scenario.verify(contract.data.finished)
    scenario.verify(contract.data.winner.unwrap_some() == alice.address)
    scenario.verify(contract.data.player1_credit == sp.nat(20))

    contract.claim(_sender=alice, _now=sp.timestamp(21))
    scenario.verify(contract.balance == sp.tez(0))
    success("Version 1 dispute timeout completed successfully.")


@sp.add_test()
def test_v2_local_resolution():
    section("Version 2 local dispute resolution")
    info("Creating a scenario where local Rule 150 resolution determines the winner.")

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
        TEST_CHECKPOINT_ROUND_1,
        TEST_CHECKPOINT_ROUND_2,
        TEST_CHECKPOINT_ROUND_3,
        TEST_CHECKPOINT_ROUND_4,
    )
    scenario += contract

    alice_secret = 5
    bob_secret = 6
    alice_salt = sp.bytes("0x01010101010101010101010101010101")
    bob_salt = sp.bytes("0x02020202020202020202020202020202")
    alice_trace_salt = sp.bytes("0x03030303030303030303030303030303")
    bob_trace_salt = sp.bytes("0x04040404040404040404040404040404")

    contract.join(
        make_commitment(alice.address, alice_secret, alice_salt),
        _sender=alice,
        _amount=sp.tez(10),
        _now=sp.timestamp(0),
    )
    contract.join(
        make_commitment(bob.address, bob_secret, bob_salt),
        _sender=bob,
        _amount=sp.tez(10),
        _now=sp.timestamp(1),
    )
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

    (
        expected_bit,
        checkpoint1,
        checkpoint2,
        checkpoint3,
        checkpoint4,
    ) = build_trace_for_contract(
        alice_secret,
        bob_secret,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_CHECKPOINT_ROUND_1,
        TEST_CHECKPOINT_ROUND_2,
        TEST_CHECKPOINT_ROUND_3,
        TEST_CHECKPOINT_ROUND_4,
    )

    contract.commit_trace(
        make_trace_commitment(
            alice.address,
            expected_bit,
            sp.bytes(checkpoint1),
            sp.bytes(checkpoint2),
            sp.bytes(checkpoint3),
            sp.bytes(checkpoint4),
            alice_trace_salt,
        ),
        _sender=alice,
        _now=sp.timestamp(4),
    )
    contract.commit_trace(
        make_trace_commitment(
            bob.address,
            1 - expected_bit,
            sp.bytes("0x55"),
            sp.bytes(checkpoint2),
            sp.bytes(checkpoint3),
            sp.bytes(checkpoint4),
            bob_trace_salt,
        ),
        _sender=bob,
        _now=sp.timestamp(5),
    )

    contract.reveal_trace(
        sp.record(
            final_bit=expected_bit,
            checkpoint1=sp.bytes(checkpoint1),
            checkpoint2=sp.bytes(checkpoint2),
            checkpoint3=sp.bytes(checkpoint3),
            checkpoint4=sp.bytes(checkpoint4),
            salt=alice_trace_salt,
        ),
        _sender=alice,
        _now=sp.timestamp(6),
    )
    contract.reveal_trace(
        sp.record(
            final_bit=1 - expected_bit,
            checkpoint1=sp.bytes("0x55"),
            checkpoint2=sp.bytes(checkpoint2),
            checkpoint3=sp.bytes(checkpoint3),
            checkpoint4=sp.bytes(checkpoint4),
            salt=bob_trace_salt,
        ),
        _sender=bob,
        _now=sp.timestamp(7),
    )

    scenario.verify(contract.data.phase == sp.nat(4))

    contract.open_dispute(_sender=alice, _now=sp.timestamp(8))
    contract.submit_checkpoint(
        sp.record(
            round_index=sp.nat(1),
            state_hash=sp.bytes("0x1010"),
            proof=sp.bytes("0xaaaa"),
        ),
        _sender=alice,
        _now=sp.timestamp(9),
    )
    contract.submit_checkpoint(
        sp.record(
            round_index=sp.nat(1),
            state_hash=sp.bytes("0x2020"),
            proof=sp.bytes("0xbbbb"),
        ),
        _sender=bob,
        _now=sp.timestamp(10),
    )

    contract.resolve_dispute(
        sp.record(
            cell_index=sp.nat(0),
            left=sp.nat(0),
            center=sp.nat(1),
            right=sp.nat(1),
            player1_next=sp.nat(0),
            player2_next=sp.nat(1),
        ),
        _sender=alice,
        _now=sp.timestamp(11),
    )

    scenario.verify(contract.data.finished)
    scenario.verify(contract.data.winner.unwrap_some() == alice.address)
    scenario.verify(contract.data.player1_credit == sp.nat(20))

    contract.claim(_sender=alice, _now=sp.timestamp(12))
    scenario.verify(contract.balance == sp.tez(0))
    success("Version 2 local dispute resolution completed successfully.")


if __name__ == "__main__":
    success("test_contract.py executed. SmartPy registered the contract test scenarios.")
