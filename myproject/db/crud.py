from db.database import Session
from db.models import PlayerHistory

def add_player_history(player):
    """Add player history to database"""
    session = Session()

    player_history = PlayerHistory(
        session_id=player.session.id,
        participant_id=player.participant.id,
        role_type=player.side,
        choice=player.cooperate,
        g_survey=player.g_responses,
        advice=player.participant.vars['g_advice'],
        ancestor_session_id=player.ancestor_session_id,
        ancestor_participant_id=player.ancestor_participant_id,
        ancestor_advice=player.ancestor_advice,
    )
    session.add(player_history)
    session.commit()
    session.close()


def get_ancestor_players(ancestor_session_id):
    """Get all players in a session with a specific role"""
    session = Session()
    histories = (
        session.query(PlayerHistory)
        .filter(PlayerHistory.session_id == ancestor_session_id)
        .all()
    )
    session.close()
    return histories