import pytest

from ugjcs.domain.ids import TrackingCode


def test_tracking_code_formats_year_and_zero_padded_sequence() -> None:
    assert TrackingCode.mint(2026, 42).value == "UGJCS-2026-0042"


def test_tracking_code_pads_to_four_digits() -> None:
    assert TrackingCode.mint(2026, 7).value == "UGJCS-2026-0007"


def test_tracking_code_accepts_sequences_beyond_four_digits() -> None:
    assert TrackingCode.mint(2026, 12345).value == "UGJCS-2026-12345"


@pytest.mark.parametrize("sequence", [0, -1])
def test_tracking_code_rejects_non_positive_sequence(sequence: int) -> None:
    with pytest.raises(ValueError, match="sequence must be positive"):
        TrackingCode.mint(2026, sequence)


def test_tracking_code_parses_its_own_output() -> None:
    minted = TrackingCode.mint(2026, 42)
    assert TrackingCode.parse(minted.value) == minted


def test_tracking_code_rejects_malformed_input() -> None:
    with pytest.raises(ValueError, match="malformed tracking code"):
        TrackingCode.parse("UGJCS/2026/42")
