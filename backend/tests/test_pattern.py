import pytest

from app.pattern import parse_pattern


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1-0-1", (1, 0, 1)),
        ("½-0-1", (0.5, 0, 1)),
        ("0.5-0-1", (0.5, 0, 1)),
        ("1½-1-0", (1.5, 1, 0)),
        ("1 - 1 - 1", (1, 1, 1)),
    ],
)
def test_valid_patterns(text, expected):
    assert parse_pattern(text) == expected


@pytest.mark.parametrize(
    "text", ["", "1-0", "1-0-1-1", "0-0-0", "a-0-1", "-1-0-1", "0.3-0-1", "11-0-1", "1,0,1"]
)
def test_invalid_patterns(text):
    with pytest.raises(ValueError):
        parse_pattern(text)


def test_api_rejects_bad_pattern(client, auth, elder_with_medicine):
    _, medicine_id = elder_with_medicine
    r = client.post(
        f"/medicines/{medicine_id}/schedules",
        json={"pattern": "1-x-1", "start_date": "2026-01-01"},
        headers=auth,
    )
    assert r.status_code == 422
