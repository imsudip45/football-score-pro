"""Service-level tests that run without the Qt UI."""

import pytest

from main import ServiceContainer


def _team(team_id, name):
    return {
        "id": team_id,
        "full_name": name,
        "short_name": name[:3].upper(),
        "manager": "Manager",
        "head_coach": "Coach",
        "players": [
            {
                "id": f"{team_id}_{n}",
                "team_id": team_id,
                "full_name": f"{name} Player {n}",
                "short_name": f"P. {n}",
                "jersey_number": n,
                "position": "GK" if n == 1 else "DEF" if n <= 5 else "MID" if n <= 8 else "FWD",
            }
            for n in range(1, 12)
        ],
    }


@pytest.fixture
def services(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    container = ServiceContainer()
    container.initialize()
    yield container
    container.shutdown()


@pytest.fixture
def match_id(services):
    teams = services.get_service("team_service")
    assert teams.import_from_json_data(_team("home", "Home Club")).success
    assert teams.import_from_json_data(_team("away", "Away Club")).success
    result = services.get_service("match_service").create_match(
        {
            "home_team": teams.get_team_by_id("home"),
            "away_team": teams.get_team_by_id("away"),
            "venue": "Test Ground",
            "match_date": "2025-01-01",
            "match_time": "15:00",
        }
    )
    assert result.success, result.errors
    return result.created_id


def test_match_needs_two_different_teams(services):
    teams = services.get_service("team_service")
    assert teams.import_from_json_data(_team("home", "Home Club")).success
    team = teams.get_team_by_id("home")
    result = services.get_service("match_service").create_match(
        {"home_team": team, "away_team": team, "venue": "X", "match_date": "2025-01-01", "match_time": "15:00"}
    )
    assert not result.success


@pytest.mark.parametrize(
    "officials",
    [
        # Keys sent by the match setup tab
        {"referee": "Ref", "assistant_referee_1": "AR1", "assistant_referee_2": "AR2", "avar_referee": "AVAR"},
        # Keys used by the model and older callers
        {"referee": "Ref", "linesman_1": "AR1", "linesman_2": "AR2", "assistant_var": "AVAR"},
    ],
)
def test_assign_officials_accepts_both_key_styles(services, match_id, officials):
    match_service = services.get_service("match_service")
    result = match_service.assign_officials(match_id, {**officials, "var_referee": "VAR", "fourth_official": "4th"})
    assert result.success, result.errors
    assigned = match_service.get_match_by_id(match_id).officials
    assert (assigned.linesman_1, assigned.linesman_2, assigned.avar_referee) == ("AR1", "AR2", "AVAR")
