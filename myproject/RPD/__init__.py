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
    PAYOFF_I = cu(5) # interpretation payoff
    NUM_ROUNDS = 60
    C_TAG = '1' # label for cooperation
    D_TAG = '2' # label for defection
    num_match = 4
    PLAYERS_PER_GROUP = 2
    delta = 1
    gamma = 1
    inactive_color = ["#FAE5CB", "#CBE6FA"]
    active_color = ["SandyBrown","LightSkyBlue"]
    history_color = active_color
    outcome_color = ["Orange","DeepSkyBlue"]
    button_color = outcome_color
    hover_color = ["#FE9900","#00C4FE"]


class Subsession(BaseSubsession):
    dice_roll = models.IntegerField(initial=-10)
    first_period = models.BooleanField(initial=True)  # True if it is the first period of a match
    last_period = models.BooleanField(initial=False)  # True if it is the last period of a match
    match_number = models.IntegerField(initial=0)
    period_number = models.IntegerField(initial=1)
    current_gen = models.IntegerField(initial=0)
    current_gen_first_round = models.IntegerField(initial=1)
    delta = models.IntegerField(initial = C.delta)
    stop_session = models.BooleanField(initial = False)
    payoff_round = models.IntegerField(initial = 1)
    payoff_match = models.IntegerField(initial = -1)
    round = models.IntegerField(initial = 1)

class Group(BaseGroup):
    number = models.IntegerField()

class Player(BasePlayer):
    # Game fields
    action = models.StringField(initial=C.D_TAG)
    cooperate = models.BooleanField(
        choices=[[True, C.C_TAG], [False, C.D_TAG]],
        doc="""This player's decision""",
        widget=widgets.RadioSelect,
        initial= False,
    )
    react = models.BooleanField(
        choices=[[True, C.C_TAG], [False, C.D_TAG]],
        doc="""This player's decision""",
        widget=widgets.RadioSelect,
        initial= False,)
    # ID fields
    side = models.BooleanField(initial = False)


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
    if nround == 1:
        roll = dice_rolls[1]
    else:
        subsession.current_gen = subsession.in_round(nround - 1).current_gen
        subsession.match_number = subsession.in_round(nround - 1).match_number
        if subsession.in_round(nround-1).last_period:
            subsession.period_number = 1
        else:
            subsession.period_number = subsession.in_round(nround-1).period_number + 1
            subsession.round = subsession.in_round(nround-1).round + 1
            subsession.current_gen_first_round = subsession.in_round(nround-1).current_gen_first_round
            if subsession.period_number == 3:
                subsession.round = subsession.round - 1


    players = subsession.get_players()
    if nround == subsession.current_gen_first_round:
        subsession.group_randomly()
        subsession.period_number = 1
        subsession.current_gen = subsession.current_gen + 1
        #subsession.group_randomly()
        for group in subsession.get_groups():
            group_players = group.get_players()
            random.shuffle(group_players)
            sides = [True, False]
            for p, side in zip(group_players, sides):
                p.side = side
    else:
        subsession.group_like_round(subsession.current_gen_first_round)
        for p in players:
            p.participant.vars['match_history'] = {}
            p.participant.vars['match_payoffs'] = []
            p.side = p.in_round(nround - 1).side
    if subsession.period_number != 2 and nround >= 3:
        roll = dice_rolls[nround - 1]
        roll1 = -1
        if subsession.period_number == 3:
            roll1 = subsession.in_round(nround - 2).dice_roll
        if roll1 > delta or roll > delta:
            subsession.last_period = True
            subsession.match_number += 1
            if roll1 > delta:
                subsession.payoff_round = nround - 2
                print(nround)
            if subsession.match_number >= C.num_match:
                subsession.payoff_match = np.random.randint(1, subsession.match_number+1)
    subsession.delta = delta
    subsession.dice_roll = roll

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






class React(Page):
    form_model = 'player'
    form_fields = ['react']

    @staticmethod
    def is_displayed(player: Player):
        return (player.subsession.period_number == 2 or player.subsession.period_number == 3)
    @staticmethod
    def vars_for_template(player: Player):
        n = player.subsession.round_number
        scenario = player.subsession.period_number - 1
        if scenario == 1:
            p_cooperate = player.in_round(n-1).cooperate
            opp_cooperate = True
            #history = {'P1': {'period': '1', 'cooperate':p_cooperate, 'name_action': player.in_round(n-1).action,
                            #'opp_cooperate':opp_cooperate,'name_opp_action': 1}}
        else:
            p_cooperate = player.in_round(n-2).cooperate
            opp_cooperate = False
            #history = {'P1': {'period': '1', 'cooperate':p_cooperate, 'name_action': player.in_round(n-1).action,
                            #'opp_cooperate':opp_cooperate,'name_opp_action': 2}}
        return {
            'period':2,
            'round_number': player.subsession.round_number,
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'Dbutton_color': C.button_color[False],
            'Cbutton_color': C.button_color[True],
            'Dbutton_hover': C.hover_color[False],
            'Cbutton_hover': C.hover_color[True],
            'version':scenario,
            'my_decision':p_cooperate,
            'opp_cooperate':opp_cooperate,
            'my_color':"style=\"background:"+C.inactive_color[p_cooperate]+";\"",
            'opp_color':"style=\"background:"+C.inactive_color[opp_cooperate]+";\"",
            'outcome_color':"style=\"background:"+C.outcome_color[opp_cooperate]+";\"",
            'first_period': player.subsession.first_period,
            'history': [],
            'delta':player.subsession.delta,
            'CTAG':C.C_TAG,
            'DTAG':C.D_TAG,
            'round': player.subsession.round_number,
            'session':player.session_id,
            'pay': player.participant.vars['match_payoffs'],
        }

class Decision(Page):
    form_model = 'player'
    form_fields = ['cooperate']
    @staticmethod
    def is_displayed(player: Player):
        return (player.subsession.period_number != 2 and player.subsession.period_number != 3)
    @staticmethod
    def vars_for_template(player: Player):
        return {
            'opponent': get_opponent(player),
            'first_period': player.subsession.round == 1,
            'round_number': player.subsession.round_number,
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'Dbutton_color': C.button_color[False],
            'Cbutton_color': C.button_color[True],
            'Dbutton_hover': C.hover_color[False],
            'Cbutton_hover': C.hover_color[True],
            'period': player.subsession.round,
            'history': player.participant.vars['match_history'],
            'delta':player.subsession.delta,
            'CTAG':C.C_TAG,
            'DTAG':C.D_TAG,
            'session':player.session_id,
            'match':player.subsession.match_number,
        }

class Results1WaitPage(WaitPage):
    @staticmethod
    def is_displayed(subsession: Subsession):
        return subsession.period_number == 3

    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        n = subsession.round_number
        for group in subsession.get_groups():
            for p in group.get_players():
                opp = get_opponent(p)
                p.cooperate = p.react
                if opp.in_round(n-2).cooperate:
                    p.cooperate = p.in_round(n-1).react

class ResultsWaitPage(WaitPage):
    wait_for_all_groups = True
    template_name = 'RPD/ResultsWaitPage.html'
    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.period_number != 2
    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        for group in subsession.get_groups():
            n = subsession.round_number
            if group.subsession.period_number == 3:
                for p in group.get_players():
                    opp = get_opponent(p)
                    p.cooperate = p.react
                    if opp.in_round(n - 2).cooperate:
                        p.cooperate = p.in_round(n - 1).react

            set_payoffs(group)
            round = str(group.subsession.round)
            for p in group.get_players():
                if p.subsession.last_period:
                    p.participant.vars['match_payoffs'].append(p.payoff)
                opp = get_opponent(p)
                if p.cooperate:
                    p.action = C.C_TAG
                if opp.cooperate:
                    opp.action = C.C_TAG
                if p.subsession.round_number <= p.subsession.payoff_round:
                    p.participant.vars['match_history']['P' + round] = {
                        'period': round,
                        'cooperate':p.cooperate,
                        'name_action': p.action,
                        'opp_cooperate':opp.cooperate,
                        'name_opp_action': opp.action
                    }
                    continue



    @staticmethod
    def vars_for_template(player: Player):
        opp = get_opponent(player)
        return {
            'first_period': player.subsession.period_number == 1,
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'Dbutton_color': C.active_color[False],
            'Cbutton_color': C.active_color[True],
            'history': player.participant.vars['match_history'],
            'my_color':"style=\"background:"+C.inactive_color[player.cooperate]+";\"",
            'my_decision':player.cooperate,
            'period': player.subsession.round,
            'first_period': player.subsession.period_number==1,
        }

class Results1(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.period_number == 3

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        n = player.subsession.round_number-2 # first round
        return dict(
            first_period = False,
            payoff_round = player.subsession.payoff_round,
            round_number = player.subsession.round_number,
            opponent=opponent,
            same_choice=player.in_round(n).cooperate == opponent.in_round(n).cooperate,
            my_decision=player.in_round(n).cooperate,
            opp_decision=opponent.in_round(n).cooperate,
            roll = player.subsession.in_round(n).dice_roll,
            history = player.participant.vars['match_history'],
            history_Ccolor = "style=\"background-color:"+C.history_color[True]+"\"",
            history_Dcolor = "style=\"background-color:"+C.history_color[False]+"\"",
            Dbutton_color= C.active_color[False],
            Cbutton_color= C.active_color[True],
            my_color="style=\"background:"+C.inactive_color[player.in_round(n).cooperate]+";\"",
            opp_color="style=\"background:"+C.inactive_color[opponent.in_round(n).cooperate]+";\"",
            outcome_color="style=\"background:"+C.outcome_color[opponent.in_round(n).cooperate]+";\"",
            last_per=player.subsession.last_period,
            delta=player.subsession.delta,
            match=player.subsession.match_number,
            period= player.subsession.round,
            opp = get_opponent(player),)


class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.period_number >= 3 and player.subsession.payoff_round != player.subsession.round_number - 2

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        p_cooperate = player.cooperate
        opp_cooperate = opponent.cooperate

        return dict(
            opponent=opponent,
            same_choice=p_cooperate == opp_cooperate,
            period = player.subsession.round,
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
            last_per=player.subsession.last_period,
            delta=player.subsession.delta,
            match=player.subsession.match_number,
            pay = player.participant.vars['match_payoffs'],
            first_period = False,
            opp = get_opponent(player),)

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.payoff = 0


class EndOfMatch(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.match_number >= C.num_match and player.subsession.last_period

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        player.payoff = player.participant.vars['match_payoffs'][player.subsession.payoff_match-1]
        return dict(
            first_period = False,
            roll=player.subsession.dice_roll,
            round = player.subsession.round_number,
            history_Ccolor = "style=\"background-color:"+C.history_color[True]+"\"",
            history_Dcolor = "style=\"background-color:"+C.history_color[False]+"\"",
            Dbutton_color= C.active_color[False],
            Cbutton_color= C.active_color[True],
            opponent=opponent,
            sessionid=player.session.id,
            same_choice=player.cooperate == opponent.cooperate,
            my_decision=player.field_display('cooperate'),
            opponent_decision=opponent.field_display('cooperate'),
            history = player.participant.vars['match_history'],
            delta=player.subsession.delta,
            per= player.subsession.round,
            payoff=player.participant.payoff,
            money_payoff = player.participant.payoff_plus_participation_fee()
        )

page_sequence = [
                 Decision, React,
                 ResultsWaitPage, Results1,
                  Results,EndOfMatch]


#page_sequence = [Introduction, Decision, ResultsWaitPage, ResultsPage, WaitGroup, Results]
