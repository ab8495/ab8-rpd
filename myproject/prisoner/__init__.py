from otree.api import *
import numpy as np
import time
import math
import pickle
import random
from db.database import create_database_tables
from db.crud import get_ancestor_players, add_player_history


doc = """
This is an intergenerational "Prisoner's Dilemma". Two players are asked separately
whether they want to cooperate or defect. Their choices directly determine the
payoffs.
"""

## Random seed
# delta
# survey

class C(BaseConstants):
    NAME_IN_URL = 'prisoner'
    INSTRUCTIONS_TEMPLATE = 'prisoner/instructions.html'
    INSTRUCTIONS_SURVEY = 'prisoner/instructions-survey.html'
    PAYOFF_CC = 60
    PAYOFF_CD = 10
    PAYOFF_DC = 100
    PAYOFF_DD = 35
    PAYOFF_I = cu(4) # interpretation payoff
    NUM_ROUNDS = 300
    C_TAG = '1' # label for cooperation
    D_TAG = '2' # label for defection
    num_gen = 1
    num_groups = 1
    PLAYERS_PER_GROUP = num_gen*2
    delta = 0#50
    gamma = 1
    last_gen = False # change if last generation
    genfile = 'gen'
    groupfile = 'advice'
    history = [{},
                #{'P1': {'period': '1', 'name_others_action': C_TAG, 'name_action': 'x'}},
                #{'P1': {'period': '1', 'name_others_action': D_TAG, 'name_action': 'x'}},
                #{'P1': {'period': '1', 'name_others_action': D_TAG, 'name_action': 'x'},
                 #'P2': {'period': '2', 'name_others_action': C_TAG, 'name_action': 'x'}}
                    ] # questions for advice survey


class Subsession(BaseSubsession):
    dice_roll = models.IntegerField(initial=-10)
    gen_number = models.IntegerField(initial=-10)  # which generation this round corresponds to
    first_period = models.BooleanField(initial=True)  # True if it is the first period of a match
    last_period = models.BooleanField(initial=False)  # True if it is the last period of a match
    stop_session = models.BooleanField(initial=False)  # True if the session is over
    match_number = models.IntegerField(initial=-10)
    period_number = models.IntegerField(initial=1)
    current_gen = models.IntegerField(initial=1)
    current_parity = models.BooleanField()
    first_gen = models.BooleanField(initial = False)
    last_gen_num = models.IntegerField() # number of last generation
    num_questions = models.IntegerField(initial = 0)
    delta = models.IntegerField(initial = C.delta)
    payround = models.IntegerField(initial = 1)
    adviceround = models.IntegerField(initial = 0)
    rfirst = models.BooleanField(initial = False)



class Group(BaseGroup):
    gen = models.IntegerField()

class Player(BasePlayer):
    # Game fields
    cum_payoff = models.CurrencyField(initial=0)
    final_period = models.BooleanField(initial = False) # ready to receive payoff, leave experiment
    points = models.CurrencyField(initial=-5)
    action = models.StringField(initial=C.D_TAG)
    cooperate = models.BooleanField(
        choices=[[True, C.C_TAG], [False, C.D_TAG]],
        doc="""This player's decision""",
        widget=widgets.RadioSelect,
        initial= False,
    )
    session_gen = models.IntegerField(initial = 1)
    decision = models.BooleanField(initial = False)
    payround = models.IntegerField(initial = 0)
    # advice
    ancestor_advice = models.LongStringField(label="Advice to you", default="")
    ancestor_session_id = models.IntegerField(default=0)
    ancestor_participant_id = models.IntegerField(default=0)
    r_advice = models.LongStringField(default= '') # received advice
    g_advice = models.LongStringField(initial = '',label="What message would you like to pass to the next participant?")
    # ID fields
    side = models.BooleanField(initial = False)
    stage = models.IntegerField(initial=-1)
    tag = models.StringField(initial = "")
    # Survey fields
    rfirst = models.BooleanField(initial = False)
    rdone = models.BooleanField(initial = False) # done survey on received advice
    r_survey = models.BooleanField(initial = True) # interpreting received advice
    interpret = models.BooleanField()
    clear = models.BooleanField(label="Does the advice clearly indicate what to do in this scenario?")
    g_responses = models.BooleanField(initial = False)
    r_responses = models.BooleanField(initial = False)


# FUNCTIONS
def creating_session(subsession: Subsession):
    nround = subsession.round_number # current round
    ## ROLL Round incrementing

    # draw random number for each round
    seed = random.seed(a=None, version=2)
    random.seed(a=seed, version=2)
    dice_rolls = np.random.randint(1, 100, C.NUM_ROUNDS+1).tolist()
    subsession.session.vars['dice_rolls'] = dice_rolls

    if C.last_gen:
        delta = 1-(1-C.delta)/(1+C.gamma)
    else:
        delta = C.delta
    num_gen = C.num_gen

    roll = dice_rolls[nround]
    if roll > delta: # last period for generation
        subsession.last_period = True
        subsession.rfirst = bool(random.getrandbits(1))
        if subsession.period_number > 1:
            subsession.payround = np.random.randint(1,subsession.period_number)
        if subsession.current_gen >= C.num_gen:
            subsession.stop_session = True
        else:
            subsession.stop_session = False


    ## player advice/incrementing
    # initialize roles and draw advice
    players = subsession.get_players()
    if nround == 1:
        create_database_tables()
        #subsession.group_randomly()
        ancestor_session_id = subsession.session.config['ancestor_session_id']
        ancestor_players = get_ancestor_players(ancestor_session_id)
        # randomly assign groups, generations, dynasty
        for group in subsession.get_groups():
            gens = []
            for i in range(1,C.num_gen+1):
                gens = gens + [i, i]
            random.shuffle(gens)
            group_players = group.get_players()
            for p, gen in zip(group_players, gens):
                p.session_gen = gen
            for gen in range(1,C.num_gen+1):
                gen_players = [player for player in group_players if player.session_gen == gen]
                random.shuffle(gen_players)
                sides = [True, False]
                for p, side in zip(gen_players, sides):
                    p.side = side

        # Pass advice in first round (with random ancestors)
        for p in players:
            p.participant.vars['interprets'] = []
            p.participant.vars['r_advice'] = ''
            p.participant.vars['g_advice'] = ''
            p.participant.vars['match_history'] = {}
            if p.session_gen == 1:
                p.stage = 0 # indicate player is active
                if p.session.config['gen_start']:
                    # no advice
                    subsession.first_gen = True
                else:
                    # Filter players by role
                    #ancestor_role_players = [player for player in ancestor_players]
                    # Randomly select a player one of the players that share the same role
                    ancestor = random.choice(ancestor_players)
                    # Remove the selected player from the list of ancestors
                    ancestor_players.remove(ancestor)

                    p.ancestor_session_id = ancestor_session_id
                    p.ancestor_participant_id = ancestor.participant_id
                    p.participant.vars['r_advice'] = ancestor.g_advice

    # continue advice/ increment player attributes
    if nround > 1:
        # increment session generation attributes
        if subsession.in_round(nround - 1).last_period:  # new generation
            period = 1
            gen = subsession.in_round(nround - 1).current_gen + 1
            subsession.first_period = True
        else:  # same generation
            period = subsession.in_round(nround - 1).period_number + 1
            gen = subsession.in_round(nround - 1).current_gen
            subsession.first_gen = subsession.in_round(nround - 1).first_gen
            subsession.first_period = False
        subsession.period_number = period  # increments period number
        subsession.current_gen = gen

        for p in players:
            p.side = p.in_round(nround - 1).side
            p.session_gen = p.in_round(nround - 1).session_gen
        #active_players = [player for player in players if player.session_gen == subsession.current_gen]
        for p in players:
            p.participant.vars['wait'] = False
            if p.session_gen == subsession.current_gen: # Pass advice in later generations (inheritance already random from role)
                p.stage = 0
            if p.session_gen < p.subsession.current_gen:  # if retired, recall advice, survey generations, increment stage
                p.stage = p.in_round(p.round_number - 1).stage + 1
                if p.session_gen == 1:
                    p.r_survey = False
                else:
                    if p.stage < p.subsession.num_questions:
                        p.r_survey = p.rfirst
                    else:
                        p.r_survey = not p.rfirst
            if p.session_gen > p.subsession.current_gen:
                p.stage = -1
                p.participant.vars['wait'] = True
            p.rfirst = p.in_round(p.round_number - 1).rfirst
            p.payround = p.in_round(p.round_number - 1).payround
    subsession.delta = delta
    subsession.num_questions = len(C.history)
    subsession.dice_roll = roll

def opp(player: Player): # identify opponent
    for j in player.get_others_in_group():
        if player.session_gen == j.session_gen:
            return j

def pred(player: Player): # identify predecessor
    for j in player.get_others_in_group():
        if player.session_gen == j.session_gen + 1 and player.side == j.side:
            return j

def succ(player: Player): # identify successor
    for j in player.get_others_in_group():
        if player.session_gen == j.session_gen - 1 and player.side == j.side:
            return j

def sort_response(player: Player):
    N = player.subsession.num_questions
    if player.session_gen == 1:
        player.g_responses = player.participant.vars['interprets'][0: N - 1]
    if player.rfirst:
        player.r_responses = player.participant.vars['interprets'][0: N - 1]
        player.g_responses = player.participant.vars['interprets'][N:2 * N - 1]
    else:
        player.g_responses = player.participant.vars['interprets'][0: N - 1]
        player.r_responses = player.participant.vars['interprets'][N:2 * N - 1]


def g_advice_score(player: Player): # score points for given advice
    succ_resp = succ(player).r_responses
    score = len(np.where(player.g_responses == succ_resp)[0])*C.PAYOFF_I # count matching interpretations
    return score

def r_advice_score(player: Player): # score points for received advice
    pred_resp = pred(player).g_responses
    score = len(np.where(player.r_responses == pred_resp)[0]) * C.PAYOFF_I # count matching interpretations
    return score

def set_payoffs(group: Group):
    for p in group.get_players():
        if p.stage == 0:
            j = opp(p)
            payoff_matrix = {
               (False, True): C.PAYOFF_DC,
                (True, True): C.PAYOFF_CC,
                (False, False): C.PAYOFF_DD,
                (True, False): C.PAYOFF_CD,
            }
            p.payoff = payoff_matrix[(p.cooperate,j.cooperate)]
            #if p.round_number != 1:
            #    p.cum_payoff += + p.payoff
            #else:
            if p.subsession.last_period:
                #payround = p.subsession.payround + p.round0
                p.cum_payoff = p.payoff


        #p.participant.vars['pd_points'] += p.points
        #p.participant.payoff = round(p.participant.vars['pd_points'] * group.session.config['pd_conversion'], 2)
        #p.participant.vars['pd_dollars'] = p.participant.payoff
        # p.save()

# PAGES
class Initialize(WaitPage):
    wait_for_all_groups = True

    def vars_for_template(player: Player):
        if player.session_gen > 1 and player.subsession.round_number > 1:
            #player.r_advice = pred(player).in_round(player.subsession.round_number - 1).g_advice
            player.ancestor_session_id = pred(player).session_id
            player.ancestor_participant_id = pred(player).participant_id



class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        N = player.subsession.num_questions
        return (player.subsession.first_period and player.stage == 0) or player.stage == 1 or (player.stage == N+1 and not player.participant.vars['wait'])
    @staticmethod
    def vars_for_template(player: Player):
        tag = str(player.session_gen)
        if player.side:
            tag += 'A'
        else:
            tag += 'B'
        return {
            'first_period': player.subsession.first_period,
            'wait': player.participant.vars['wait'],
            'r_advice': player.participant.vars['r_advice'],
            'gam_gen': player.subsession.current_gen,
            'gen': player.session_gen,
            'first_gen': player.subsession.first_gen,
            'delta':player.subsession.delta,
            'tag': tag,
            'stage':player.stage,
            'rsurvey':player.r_survey,
            'round': player.subsession.round_number,
            'per': player.subsession.period_number,
            'payI': C.PAYOFF_I,
        }

class Decision(Page):
    form_model = 'player'
    form_fields = ['cooperate']


    @staticmethod
    def is_displayed(player: Player):
        return player.stage == 0
    @staticmethod
    def vars_for_template(player: Player):
        tag = str(player.session_gen)
        if player.side:
            tag += 'A'
        else:
            tag += 'B'
        #player.participant.vars['match_history']['P' + p.subsession.period_number] = {}
        return {
            'interprets': player.participant.vars['interprets'],
            'first_gen': player.subsession.first_gen,
            'first_period': player.subsession.first_period,
            'history': player.participant.vars['match_history'],
            'delta':player.subsession.delta,
            'r_advice': player.participant.vars['r_advice'],
            'gam_gen': player.subsession.current_gen,
            'CTAG':C.C_TAG,
            'DTAG':C.D_TAG,
            'gen': player.session_gen,
            'tag': tag,
            'round': player.subsession.round_number,
            'per': player.subsession.period_number,
        }

class Survey(Page):
    form_model = 'player'
    form_fields = ['interpret','clear']

    @staticmethod
    def is_displayed(player: Player):
        return player.stage > 0 and not player.participant.vars['wait']

    @staticmethod
    def vars_for_template(player: Player):
        history = C.history
        N = player.subsession.num_questions
        question = (player.stage-1) % N
        r_survey = player.r_survey
        if r_survey:
            advice = player.participant.vars['r_advice'] # r_advice survey
        else:
            advice = player.participant.vars['g_advice'] # g_advice survey
        if player.stage == N*2-1:
            player.participant.vars['wait'] = True
        if player.stage == N and (C.last_gen or player.session_gen == 1): # player done
            player.participant.vars['wait'] = True
            if C.last_gen:
                player.final_period = True
        historyq = history[question]
        return {
            'advice': advice,
            'r': r_survey,
            'history':historyq,
            'first':historyq == {},
            'delta':player.subsession.delta,
            'CTAG':C.C_TAG,
            'DTAG':C.D_TAG,
            'stage':player.stage,
            'q':question
        }

class ResultsWaitPage(WaitPage):
    #template_name = 'prisoner/ResultsWaitPage.html'
    #wait_for_all_groups = True
    #@staticmethod
    #def is_displayed(player: Player):

    @staticmethod
    def after_all_players_arrive(group: Group):
        set_payoffs(group)
        period_number = str(group.subsession.period_number)
        N = group.subsession.num_questions
        for p in group.get_players():
            j = opp(p)
            if p.stage > 0 and not p.participant.vars['wait']: # active survey players
                hist = p.participant.vars['interprets']
                p.participant.vars['interprets'] = [hist, p.interpret]
            if p.stage > 0 and p.participant.vars['wait']: # graduate inactive survey players once successor finishes r questions
                if p.session_gen < C.num_gen: # not last generation
                    j = succ(p)
                    if (j.stage >= N and j.rfirst) or (j.stage >= 2*N and not j.rfirst): # successor done questions on received advice
                        p.final_period = True
                else:
                    p.final_period = True
            if p.stage == 0: # active players
                if p.cooperate:
                    p.action = C.C_TAG
                if j.cooperate:
                    j.action = C.C_TAG
            p.participant.vars['match_history']['P' + period_number] = {
                'period': period_number,
                'name_others_action': j.action,
                'name_action': p.action
            }


    @staticmethod
    def vars_for_template(player: Player):
        tag = str(player.session_gen)
        if player.side:
            tag += 'A'
        else:
            tag += 'B'
        match_list = []
        advice = player.participant.vars['r_advice']
        return {
            'first_gen': player.subsession.first_gen,
            'first_period': player.subsession.first_period,
            'r_advice': advice,
            'match_list': match_list,
            'current_match': str(player.session_gen),
            'tag': tag,
            'per': player.subsession.period_number,
            'opp': opp(player),
        }






class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.stage == 0

    @staticmethod
    def vars_for_template(player: Player):
        opponent = opp(player)
        return dict(
            opponent=opponent,
            same_choice=player.cooperate == opponent.cooperate,
            stop=player.subsession.stop_session,
            my_decision=player.field_display('cooperate'),
            opponent_decision=opponent.field_display('cooperate'),
            roll = player.subsession.dice_roll,
            history = player.participant.vars['match_history'],
            first_gen= player.subsession.first_gen,
            last_per=player.subsession.last_period,
            delta=player.subsession.delta,
            first_period = False,
            r_advice = player.participant.vars['r_advice'],
            g_advice=player.participant.vars['g_advice'],
            per= player.subsession.period_number,
            opp = opp(player),
            stage = player.stage,)

# give advice
class EndOfMatch(Page):
    form_model = 'player'
    form_fields = ['g_advice']

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.last_period and player.stage == 0 and not C.last_gen

    @staticmethod
    def vars_for_template(player: Player):
        opponent = opp(player)
        player.rfirst = player.subsession.rfirst
        player.payround = player.subsession.payround
        return dict(
            opponent=opponent,
            same_choice=player.cooperate == opponent.cooperate,
            my_decision=player.field_display('cooperate'),
            opponent_decision=opponent.field_display('cooperate'),
            first_period = player.subsession.first_period,
            history = player.participant.vars['match_history'],
            roll=player.subsession.dice_roll,
            delta=player.subsession.delta,
            r_advice=player.participant.vars['r_advice'],
            first_gen= player.subsession.first_gen,
            per= player.subsession.period_number,
            stop=player.subsession.stop_session)

class Save(WaitPage):

    @staticmethod
    def is_displayed(player: Player):
        return player.final_period

    @staticmethod
    def after_all_players_arrive(group: Group):
        for p in group.get_players():
            add_player_history(p)




class EndOfGame(Page):
    #timeout_seconds = 15
    @staticmethod
    def is_displayed(player: Player):
        return player.final_period

    @staticmethod
    def vars_for_template(player: Player):
        opponent = opp(player)
        # points for interpreting received advice
        if player.session_gen > 1:
            rpoints = r_advice_score(player)
        else:
            rpoints = 0
        # points for interpreting given advice
        if player.session_gen < C.num_gen:
            gpoints = g_advice_score(player)
        else:
            gpoints = 0
        ipoints = gpoints + rpoints # payoff from interpreting
        last_player = player.session_gen == C.num_gen
        return dict(
            opponent=opponent,
            same_choice=player.cooperate == opponent.cooperate,
            my_decision=player.field_display('cooperate'),
            opponent_decision=opponent.field_display('cooperate'),
            roll=player.subsession.dice_roll,
            r_advice=player.participant.vars['r_advice'],
            payoff=player.cum_payoff + ipoints,
            gen=player.subsession.current_gen,
            numgen= C.num_gen,
            gpoints= gpoints,
            rpoints= rpoints,
            ipoints = ipoints,
            last = last_player,
            per=player.subsession.period_number,
            stop=player.subsession.stop_session,
        )

    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        add_player_history(player)

page_sequence = [Initialize,#Introduction,
                 Decision, Survey, ResultsWaitPage, Results, EndOfMatch,
   Save, EndOfGame,]


#page_sequence = [Introduction, Decision, ResultsWaitPage, ResultsPage, WaitGroup, Results]
