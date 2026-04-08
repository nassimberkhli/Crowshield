import smartpy as sp

from contracts.contract import bet_contract
from contracts.utils import (
    JOIN_WINDOW_SECONDS,
    PROGRESS_WINDOW_SECONDS,
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
def test_security_failures():
    section("Smart contract security failure tests")
    info("Creating SmartPy scenario for invalid actions and commitment enforcement.")

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
    )
    scenario += contract

    alice_secret = 12
    bob_secret = 34
    alice_salt = sp.bytes("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    bob_salt = sp.bytes("0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")

    alice_commitment = make_commitment(alice.address, alice_secret, alice_salt)
    bob_commitment = make_commitment(bob.address, bob_secret, bob_salt)

    info("Alice joins first.")
    contract.join(
        alice_commitment,
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
        bob_commitment,
        _sender=bob,
        _amount=sp.tez(9),
        _now=sp.timestamp(1),
        _valid=False,
        _exception="INVALID_STAKE",
    )

    info("Bob joins successfully.")
    contract.join(
        bob_commitment,
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

    info("Accepting Alice's valid reveal.")
    contract.reveal(
        sp.record(secret=alice_secret, salt=alice_salt),
        _sender=alice,
        _now=sp.timestamp(4),
    )

    info("Rejecting a duplicate reveal from Alice.")
    contract.reveal(
        sp.record(secret=alice_secret, salt=alice_salt),
        _sender=alice,
        _now=sp.timestamp(5),
        _valid=False,
        _exception="ALREADY_REVEALED",
    )

    info("Rejecting a reveal from a non-registered player.")
    contract.reveal(
        sp.record(secret=bob_secret, salt=bob_salt),
        _sender=charlie,
        _now=sp.timestamp(6),
        _valid=False,
        _exception="PLAYER_NOT_REGISTERED",
    )

    info("Rejecting a reveal after the reveal deadline.")
    contract.reveal(
        sp.record(secret=bob_secret, salt=bob_salt),
        _sender=bob,
        _now=sp.timestamp(20),
        _valid=False,
        _exception="REVEAL_PHASE_OVER",
    )

    success("Security failure checks completed successfully.")


@sp.add_test()
def test_timeout_rewards_revealer():
    section("Smart contract reveal-timeout reward test")
    info("Creating SmartPy scenario where only one player reveals before timeout.")

    scenario = sp.test_scenario()

    alice = sp.test_account("alice")
    bob = sp.test_account("bob")

    contract = bet_contract.BinaryAutomatonBet(
        JOIN_WINDOW_SECONDS,
        10,
        PROGRESS_WINDOW_SECONDS,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_INIT_BATCH_SIZE,
        TEST_SIM_BATCH_SIZE,
    )
    scenario += contract

    alice_secret = 123
    bob_secret = 456
    alice_salt = sp.bytes("0x01010101010101010101010101010101")
    bob_salt = sp.bytes("0x02020202020202020202020202020202")

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

    contract.claim_timeout(
        _sender=alice,
        _now=sp.timestamp(20),
    )

    scenario.verify(contract.data.finished)
    scenario.verify(contract.data.winner.unwrap_some() == alice.address)
    scenario.verify(contract.balance == sp.tez(0))

    success("Reveal-timeout reward test completed successfully.")


@sp.add_test()
def test_progress_timeout_refunds_both_players():
    section("Smart contract progress-timeout refund test")
    info("Creating SmartPy scenario where both players reveal but the simulation stops progressing.")

    scenario = sp.test_scenario()

    alice = sp.test_account("alice")
    bob = sp.test_account("bob")

    contract = bet_contract.BinaryAutomatonBet(
        JOIN_WINDOW_SECONDS,
        60,
        10,
        TEST_TOTAL_BITS,
        TEST_TOTAL_ROUNDS,
        TEST_INIT_BATCH_SIZE,
        TEST_SIM_BATCH_SIZE,
    )
    scenario += contract

    alice_secret = 1
    bob_secret = 2
    alice_salt = sp.bytes("0x01")
    bob_salt = sp.bytes("0x02")

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

    contract.claim_timeout(
        _sender=alice,
        _now=sp.timestamp(20),
    )

    scenario.verify(contract.data.finished)
    scenario.verify(contract.data.winner.is_none())
    scenario.verify(contract.balance == sp.tez(0))

    success("Progress-timeout refund test completed successfully.")


if __name__ == "__main__":
    success("test_security.py executed. SmartPy registered the security test scenarios.")
