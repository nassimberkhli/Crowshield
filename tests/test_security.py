import smartpy as sp

from contracts.contract import bet_contract
from contracts.simulation import build_trace_for_contract
from contracts.utils import (
    JOIN_WINDOW_SECONDS,
    PROGRESS_WINDOW_SECONDS,
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
def test_security_failures():
    section("Security failure tests")
    info("Creating a scenario for invalid actions and trace commitment enforcement.")

    scenario = sp.test_scenario()

    alice = sp.test_account("alice")
    bob = sp.test_account("bob")
    charlie = sp.test_account("charlie")

    contract = bet_contract.BinaryAutomatonBet(
        JOIN_WINDOW_SECONDS,
        10,
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

    alice_secret = 12
    bob_secret = 34
    alice_salt = sp.bytes("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    bob_salt = sp.bytes("0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    alice_trace_salt = sp.bytes("0xcccccccccccccccccccccccccccccccc")
    bob_trace_salt = sp.bytes("0xdddddddddddddddddddddddddddddddd")

    info("Alice joins first.")
    contract.join(
        make_commitment(alice.address, alice_secret, alice_salt),
        _sender=alice,
        _amount=sp.tez(10),
        _now=sp.timestamp(0),
    )

    info("Rejecting a second join attempt from the same player.")
    contract.join(
        make_commitment(alice.address, 77, sp.bytes("0x01")),
        _sender=alice,
        _amount=sp.tez(10),
        _now=sp.timestamp(1),
        _valid=False,
        _exception="SAME_PLAYER",
    )

    info("Rejecting an invalid stake amount.")
    contract.join(
        make_commitment(bob.address, bob_secret, bob_salt),
        _sender=bob,
        _amount=sp.tez(9),
        _now=sp.timestamp(1),
        _valid=False,
        _exception="INVALID_STAKE",
    )

    info("Bob joins successfully.")
    contract.join(
        make_commitment(bob.address, bob_secret, bob_salt),
        _sender=bob,
        _amount=sp.tez(10),
        _now=sp.timestamp(2),
    )

    info("Rejecting an invalid reveal from Alice.")
    contract.reveal(
        sp.record(secret=999, salt=alice_salt),
        _sender=alice,
        _now=sp.timestamp(3),
        _valid=False,
        _exception="INVALID_COMMITMENT",
    )

    info("Accepting valid secret reveals.")
    contract.reveal(
        sp.record(secret=alice_secret, salt=alice_salt),
        _sender=alice,
        _now=sp.timestamp(4),
    )
    contract.reveal(
        sp.record(secret=bob_secret, salt=bob_salt),
        _sender=bob,
        _now=sp.timestamp(5),
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

    info("Both players commit their traces.")
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
        _now=sp.timestamp(6),
    )
    contract.commit_trace(
        make_trace_commitment(
            bob.address,
            expected_bit,
            sp.bytes(checkpoint1),
            sp.bytes(checkpoint2),
            sp.bytes(checkpoint3),
            sp.bytes(checkpoint4),
            bob_trace_salt,
        ),
        _sender=bob,
        _now=sp.timestamp(7),
    )

    info("Rejecting an invalid trace reveal from Alice.")
    contract.reveal_trace(
        sp.record(
            final_bit=sp.nat(1 - expected_bit),
            checkpoint1=sp.bytes(checkpoint1),
            checkpoint2=sp.bytes(checkpoint2),
            checkpoint3=sp.bytes(checkpoint3),
            checkpoint4=sp.bytes(checkpoint4),
            salt=alice_trace_salt,
        ),
        _sender=alice,
        _now=sp.timestamp(8),
        _valid=False,
        _exception="INVALID_TRACE_COMMITMENT",
    )

    info("Rejecting a trace reveal from a non-registered player.")
    contract.reveal_trace(
        sp.record(
            final_bit=expected_bit,
            checkpoint1=sp.bytes(checkpoint1),
            checkpoint2=sp.bytes(checkpoint2),
            checkpoint3=sp.bytes(checkpoint3),
            checkpoint4=sp.bytes(checkpoint4),
            salt=bob_trace_salt,
        ),
        _sender=charlie,
        _now=sp.timestamp(9),
        _valid=False,
        _exception="PLAYER_NOT_REGISTERED",
    )

    success("Security failure checks completed successfully.")


@sp.add_test()
def test_trace_commit_timeout_forfeits_absent_player():
    section("Trace commit timeout")
    info("Creating a scenario where only one player commits a trace before the deadline.")

    scenario = sp.test_scenario()

    alice = sp.test_account("alice")
    bob = sp.test_account("bob")

    contract = bet_contract.BinaryAutomatonBet(
        JOIN_WINDOW_SECONDS,
        10,
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

    alice_secret = 123
    bob_secret = 456
    alice_salt = sp.bytes("0x01010101010101010101010101010101")
    bob_salt = sp.bytes("0x02020202020202020202020202020202")
    alice_trace_salt = sp.bytes("0x03030303030303030303030303030303")

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

    contract.claim_timeout(
        _sender=alice,
        _now=sp.timestamp(20),
    )

    scenario.verify(contract.data.finished)
    scenario.verify(contract.data.winner.unwrap_some() == alice.address)
    scenario.verify(contract.data.player1_credit == sp.nat(20))

    contract.claim(
        _sender=alice,
        _now=sp.timestamp(21),
    )

    scenario.verify(contract.balance == sp.tez(0))
    success("Trace commit timeout completed successfully.")


if __name__ == "__main__":
    success("test_security.py executed. SmartPy registered the security test scenarios.")
