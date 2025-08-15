from otree.api import *
import numpy as np
import random


doc = """
This is an intergenerational "Prisoner's Dilemma". Two players are asked separately
whether they want to cooperate or defect. Their choices directly determine the
payoffs.
"""

## Random seed
# delta

class C(BaseConstants):
    NAME_IN_URL = 'RPD'
    INSTRUCTIONS_TEMPLATE = 'RPD/instructions.html'
    PAYOFF_CC = 65
    PAYOFF_CD = 10
    PAYOFF_DC = 100
    PAYOFF_DD = 35
    NUM_ROUNDS = 60
    C_TAG = '1' # label for cooperation
    D_TAG = '2' # label for defection
    num_match = 3
    PLAYERS_PER_GROUP = 2
    delta = 50
    gamma = 1
    inactive_color = ["#FAE5CB", "#CBE6FA"]
    active_color = ["SandyBrown","LightSkyBlue"]
    history_color = active_color
    outcome_color = ["Orange","DeepSkyBlue"]
    button_color = outcome_color
    hover_color = ["#FE9900","#00C4FE"]


class Subsession(BaseSubsession):
    dice_roll = models.IntegerField(initial=-10)
    last_period = models.BooleanField(initial=False)  # True if it is the last period of a match
    match_number = models.IntegerField(initial=1) # supergame number
    period_number = models.IntegerField(initial=1) # period within supergame
    payoff_match = models.IntegerField(initial = -1) # match that will be compensated

class Group(BaseGroup):
    pass
class Player(BasePlayer):
    # Game fields
    cooperate = models.BooleanField(
        choices=[[True, C.C_TAG], [False, C.D_TAG]],
        doc="""This player's decision""",
        widget=widgets.RadioSelect,
    )
    reactC = models.BooleanField(
        choices=[[True, C.C_TAG], [False, C.D_TAG]],
        doc="""This player's decision""",
        widget=widgets.RadioSelect,)
    reactD = models.BooleanField(
        choices=[[True, C.C_TAG], [False, C.D_TAG]],
        doc="""This player's decision""",
        widget=widgets.RadioSelect,)


# FUNCTIONS
def creating_session(subsession: Subsession):
    ## ROLL Round incrementing

    if subsession.session.config['gen_end']:
        delta = 1-(1-C.delta)/(1+C.gamma)
    else:
        delta = C.delta

    # draw random number for each round
    seed = random.seed(a=None, version=2)
    random.seed(a=seed, version=2)
    dice_rolls = np.random.randint(1, 101, C.NUM_ROUNDS+1).tolist()
    while sum(i > delta for i in dice_rolls[0:(C.NUM_ROUNDS)]) < C.num_match:
        dice_rolls = np.random.randint(1, 101, C.NUM_ROUNDS+1).tolist()
    subsession.session.vars['dice_rolls'] = dice_rolls

    roll = -1

    nround = subsession.round_number # current round
    if nround > 1:
        subsession.match_number = subsession.in_round(nround - 1).match_number
        subsession.period_number = subsession.in_round(nround - 1).period_number + 1
        if subsession.in_round(nround-1).last_period and subsession.period_number >2: # new match
            subsession.period_number = 1
            subsession.match_number += 1

    players = subsession.get_players()
    if subsession.period_number == 1: #new match
        subsession.group_randomly()
        for p in players: # wipe history
            p.participant.vars['match_history'] = {}
            if nround == 1: # initialize payoffs
                p.participant.vars['match_payoffs'] = []
    else:
        # keep same groups
        subsession.group_like_round(nround - 1)

    roll = dice_rolls[nround]
    subsession.dice_roll = roll
    if subsession.period_number == 2:
        subsession.last_period = subsession.in_round(nround-1).last_period
    if roll > delta:
        subsession.last_period = True
    if subsession.last_period and subsession.match_number == C.num_match:
        subsession.payoff_match = np.random.randint(1, subsession.match_number)


def get_opponent(player: Player): # identify opponent
    for j in player.get_others_in_group():
        if j != player:
            return j

def set_payoffs(group: Group):
    for p in group.get_players():
        j = get_opponent(p)
        payoff_matrix = {
            (False, True): C.PAYOFF_DC,
            (True, True): C.PAYOFF_CC,
            (False, False): C.PAYOFF_DD,
            (True, False): C.PAYOFF_CD,
        }
        p.payoff = payoff_matrix[(p.cooperate,j.cooperate)]






class ReactC(Page):
    form_model = 'player'
    form_fields = ['reactC']
    template_name = 'RPD/React.html'

    @staticmethod
    def is_displayed(player: Player):
        return (player.subsession.period_number == 2)
    @staticmethod
    def vars_for_template(player: Player):
        n = player.subsession.round_number

        # If other cooperate
        p_cooperate = player.in_round(n-1).cooperate
        opp_cooperate = True
            #history = {'P1': {'period': '1', 'cooperate':p_cooperate, 'name_action': player.in_round(n-1).action,
                            #'opp_cooperate':opp_cooperate,'name_opp_action': 1}}
        return {
            'period':2,
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'D_inactive':C.inactive_color[False],
            'C_inactive':C.inactive_color[True],
            'Dbutton_color': C.button_color[False],
            'Cbutton_color': C.button_color[True],
            'Dbutton_hover': C.hover_color[False],
            'Cbutton_hover': C.hover_color[True],
            'version':True,
            'my_decision':p_cooperate,
            'opp_cooperate':opp_cooperate,
            'my_color':"style=\"background:"+C.inactive_color[p_cooperate]+";\"",
            'opp_color':"style=\"background:"+C.inactive_color[opp_cooperate]+";\"",
            'outcome_color':"style=\"background:"+C.outcome_color[opp_cooperate]+";\"",
            'delta':C.delta,
        }

class ReactD(Page):
    form_model = 'player'
    form_fields = ['reactD']
    template_name = 'RPD/React.html'

    @staticmethod
    def is_displayed(player: Player):
        return (player.subsession.period_number == 2)
    @staticmethod
    def vars_for_template(player: Player):
        n = player.subsession.round_number
        # Other defects Defect
        p_cooperate = player.in_round(n-1).cooperate
        opp_cooperate = False
        #history = {'P1': {'period': '1', 'cooperate':p_cooperate, 'name_action': player.in_round(n-1).action,
                            #'opp_cooperate':opp_cooperate,'name_opp_action': 2}}
        return {
            'period':2,
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'D_inactive':C.inactive_color[False],
            'C_inactive':C.inactive_color[True],
            'Dbutton_color': C.button_color[False],
            'Cbutton_color': C.button_color[True],
            'Dbutton_hover': C.hover_color[False],
            'Cbutton_hover': C.hover_color[True],
            'version':False,
            'my_decision':p_cooperate,
            'opp_cooperate':opp_cooperate,
            'my_color':"style=\"background:"+C.inactive_color[p_cooperate]+";\"",
            'opp_color':"style=\"background:"+C.inactive_color[opp_cooperate]+";\"",
            'outcome_color':"style=\"background:"+C.outcome_color[opp_cooperate]+";\"",
            'delta':C.delta,
        }

class Decision(Page):
    form_model = 'player'
    form_fields = ['cooperate']
    @staticmethod
    def is_displayed(player: Player):
        return (player.subsession.period_number != 2)
    @staticmethod
    def vars_for_template(player: Player):
        return {
            'match': player.subsession.match_number,
            'group': [player.id_in_subsession, get_opponent(player).id_in_subsession],
            'first_period': player.subsession.period_number == 1,
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'Dbutton_color': C.button_color[False],
            'Cbutton_color': C.button_color[True],
            'Dbutton_hover': C.hover_color[False],
            'Cbutton_hover': C.hover_color[True],
            'period': player.subsession.period_number,
            'history': player.participant.vars['match_history'],
            'delta':C.delta,
        }

class ResultsWaitPage(WaitPage):
    wait_for_all_groups = True
    template_name = 'RPD/ResultsWaitPage.html'
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        for group in subsession.get_groups():
            n = subsession.round_number
            last_period = group.subsession.last_period

            if group.subsession.period_number == 2: ## Determine actions for this period
                if group.subsession.in_round(n-1).last_period:
                    last_period = False
                for p in group.get_players():
                    opp = get_opponent(p)
                    p.cooperate = p.reactD
                    if opp.in_round(n - 1).cooperate:
                        p.cooperate = p.reactC

            if last_period: ## Record payoffs
                set_payoffs(group)
                for p in group.get_players():
                    p.participant.vars['match_payoffs'].append(p.payoff)

            ## Add history
            round = str(group.subsession.period_number)
            for p in group.get_players():
                opp = get_opponent(p)
                p_action = C.C_TAG if p.cooperate else C.D_TAG
                opp_action = C.C_TAG if opp.cooperate else C.D_TAG

                p.participant.vars['match_history']['P' + round] = {
                        'period': round,
                        'cooperate':p.cooperate,
                        'name_action': p_action,
                        'opp_cooperate':opp.cooperate,
                        'name_opp_action': opp_action
                    }
                continue



    @staticmethod
    def vars_for_template(player: Player):
        opp = get_opponent(player)
        n = player.subsession.period_number
        if player.subsession.period_number == 2:
            coop = player.in_round(n-1).cooperate
            period = 1
        else:
            coop = player.in_round(n).cooperate
            period = player.subsession.period_number
        return {
            'first_period': period == 1,
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'Dbutton_color': C.active_color[False],
            'Cbutton_color': C.active_color[True],
            'history': player.participant.vars['match_history'],
            'my_color':"style=\"background:"+C.inactive_color[coop]+";\"",
            'my_decision':coop,
            'period': period,
        }

class Results1(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.period_number == 2

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        n = player.subsession.round_number-1 # first round
        payoff= 0
        if player.subsession.in_round(n).dice_roll>C.delta:
            payoffs = player.participant.vars['match_payoffs']
            payoff = payoffs[len(payoffs)-1]
        return dict(
            first_period = False,
            round_number = 1,
            same_choice=player.in_round(n).cooperate == opponent.in_round(n).cooperate,
            my_decision=player.in_round(n).cooperate,
            opp_decision=opponent.in_round(n).cooperate,
            next_decision = player.cooperate,
            roll = player.subsession.in_round(n).dice_roll,
            history = player.participant.vars['match_history'],
            history_Ccolor = "style=\"background-color:"+C.history_color[True]+"\"",
            history_Dcolor = "style=\"background-color:"+C.history_color[False]+"\"",
            D_inactive=C.inactive_color[False],
            C_inactive=C.inactive_color[True],
            Dbutton_color= C.active_color[False],
            Cbutton_color= C.active_color[True],
            my_color="style=\"background:"+C.inactive_color[player.in_round(n).cooperate]+";\"",
            opp_color="style=\"background:"+C.inactive_color[opponent.in_round(n).cooperate]+";\"",
            outcome_color="style=\"background:"+C.outcome_color[opponent.in_round(n).cooperate]+";\"",
            last_per=player.subsession.in_round(n).dice_roll>C.delta,
            pay = payoff,
            end=player.subsession.match_number == C.num_match,
            delta=C.delta,
            match=player.subsession.match_number,
            period= player.subsession.period_number,)
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.payoff = 0

class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        n = player.subsession.round_number
        return player.subsession.period_number >= 2 and not player.subsession.in_round(n-1).last_period

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        p_cooperate = player.cooperate
        opp_cooperate = opponent.cooperate

        payoff = 0
        if player.subsession.last_period:
            payoffs = player.participant.vars['match_payoffs']
            payoff = payoffs[len(payoffs) - 1]

        end_match = player.subsession.last_period and player.subsession.period_number >= 2
        return dict(
            first_period = False,
            period = player.subsession.period_number,
            my_decision=p_cooperate,
            opp_decision=opp_cooperate,
            roll = player.subsession.dice_roll,
            history = player.participant.vars['match_history'],
            history_Ccolor = "style=\"background-color:"+C.history_color[True]+"\"",
            history_Dcolor = "style=\"background-color:"+C.history_color[False]+"\"",
            Dbutton_color= C.active_color[False],
            Cbutton_color= C.active_color[True],
            my_color="style=\"background:"+C.inactive_color[player.cooperate]+";\"",
            opp_color="style=\"background:"+C.inactive_color[opponent.cooperate]+";\"",
            outcome_color="style=\"background:"+C.outcome_color[opponent.cooperate]+";\"",\
            last_per=end_match,
            delta=C.delta,
            match=player.subsession.match_number,)

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.payoff = 0


class EndOfMatch(Page):
    @staticmethod
    def is_displayed(player: Player):
        end_match = player.subsession.last_period and player.subsession.period_number >= 2
        return player.subsession.match_number >= C.num_match and end_match

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        player.payoff = player.participant.vars['match_payoffs'][player.subsession.payoff_match-1]
        return dict(
            match_payoffs=player.participant.vars['match_payoffs'],
            payoff_match= player.subsession.payoff_match,
            payoff=player.payoff,
            money_payoff = player.participant.payoff_plus_participation_fee()
        )

page_sequence = [
                 Decision, ReactC,ReactD,
                 ResultsWaitPage,
                  Results1,
                  Results,EndOfMatch]


#page_sequence = [Introduction, Decision, ResultsWaitPage, ResultsPage, WaitGroup, Results]
