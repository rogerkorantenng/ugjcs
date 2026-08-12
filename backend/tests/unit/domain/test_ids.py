import pytest

from ugjcs.domain.ids import TrackingCode, mint_issue_id


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


def test_tracking_code_rejects_a_year_that_is_not_four_digits() -> None:
    """`mint` must not produce a value its own `parse` would reject."""
    with pytest.raises(ValueError, match="year must be four digits"):
        TrackingCode.mint(12345, 1)


def test_the_constructor_rejects_a_value_parse_would_reject() -> None:
    """Validation on `parse` alone leaves `TrackingCode("garbage")` a legal object."""
    with pytest.raises(ValueError, match="malformed tracking code"):
        TrackingCode("garbage")


def test_mint_issue_id_is_deterministic_for_the_same_volume_and_number() -> None:
    assert mint_issue_id(3, 1) == mint_issue_id(3, 1)


def test_mint_issue_id_differs_across_volumes_and_numbers() -> None:
    assert mint_issue_id(3, 1) != mint_issue_id(3, 2)
    assert mint_issue_id(3, 1) != mint_issue_id(4, 1)


@pytest.mark.parametrize(("volume", "number"), [(0, 1), (1, 0), (-1, 1)])
def test_mint_issue_id_rejects_non_positive_volume_or_number(volume: int, number: int) -> None:
    with pytest.raises(ValueError, match="volume and number must be positive"):
        mint_issue_id(volume, number)
