from db.database import Session
from db.models import PlayerHistory

def add_player_history(player):
    """Add player history to database"""
    session = Session()

    player_history = PlayerHistory(
        session_id=player.session.id,
        dynasty=player.group.dynasty,
        participant_id=player.participant.id,
        tag=player.tag,
        group = player.group.number,
        choice=player.cooperate,
        g_advice=player.g_advice,
        g_survey='1',
        gen=player.gen,
        DynastyGroup = player.subsession.dynasty_session,
        #final=player.final_period,
        #session_end=player.session_end,
        #ancestor_session_id=player.ancestor_session_id,
        ancestor_participant_id=player.ancestor_participant_id,
        ancestor_advice=player.ancestor_advice,
    )
    session.add(player_history)
    session.commit()
    session.close()


def get_ancestor_players(dynasty_group):
    """Get all players in a session with a specific role"""
    session = Session()
    histories = (
        session.query(PlayerHistory)
        .filter(PlayerHistory.DynastyGroup == dynasty_group)
        .all()
    )
    session.close()
    return histories