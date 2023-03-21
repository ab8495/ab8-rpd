from otree.api import *
import numpy as np
import time
import math
import pickle
import random



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
    num_gen = 2
    num_groups = 1
    PLAYERS_PER_GROUP = num_gen*2
    delta = 50
    gamma = 1
    last_gen = False # change if last generation
    genfile = 'gen'
    groupfile = 'advice'
    save = False # False if first generation, else True
    history = [{},
                {'P1': {'period': '1', 'name_others_action': C_TAG, 'name_action': 'x'}},
                {'P1': {'period': '1', 'name_others_action': D_TAG, 'name_action': 'x'}},
                {'P1': {'period': '1', 'name_others_action': D_TAG, 'name_action': 'x'},
                 'P2': {'period': '2', 'name_others_action': C_TAG, 'name_action': 'x'}}
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
    gen0 = models.IntegerField(initial=0)
    current_parity = models.BooleanField()
    first_gen = models.BooleanField(initial = True)
    last_gen_num = models.IntegerField() # number of last generation
    num_questions = models.IntegerField()
    delta = models.IntegerField(initial = C.delta)
    payround = models.IntegerField(initial = 0)
    adviceround = models.IntegerField(initial = 0)
    rfirst = models.BooleanField(initial = False)



class Group(BaseGroup):
    gen = models.IntegerField()

class Player(BasePlayer):
    wait = models.BooleanField(initial = True) # waiting room
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
    gen = models.IntegerField()
    decision = models.BooleanField(initial = False)
    # advice
    r_advice = models.LongStringField(initial= '') # received advice
    g_advice = models.LongStringField(label="What message would you like "
                                            "to pass on to the participant "
                                          "that will take over for you?")
    # ID fields
    side = models.BooleanField()
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
    # draw random number for each round
    seed = random.seed(a=None, version=2)
    random.seed(a=seed, version=2)
    dice_rolls = np.random.randint(1, 100, C.NUM_ROUNDS+1).tolist()
    subsession.session.vars['dice_rolls'] = dice_rolls
    nround = subsession.round_number # current round
    #prev_roll = dice_rolls[nround - 1]
    roll = dice_rolls[nround]
    if C.last_gen:
        delta = 1-(1-C.delta)/(1+C.gamma)
    else:
        delta = C.delta
    num_gen = C.num_gen
    subsession.delta = delta
    if nround == 1: # initialize generation number
        if C.save:
            with open(C.genfile,'rb') as f:
                gen = pickle.load(f)
                f.close()
        else:
            gen = 1
        gen0 = gen-1
        period = 1
    else: # update generation/period number
        gen0 = subsession.in_round(nround - 1).gen0
        if subsession.in_round(nround - 1).last_period: # new generation
            period = 1
            gen = subsession.in_round(nround - 1).current_gen + 1
            subsession.first_period = True
        else: # same generation
            period = subsession.in_round(nround - 1).period_number + 1
            gen = subsession.in_round(nround - 1).current_gen
            subsession.first_period = False
    last_gen_num = gen0 + num_gen # final generation in this session
    if roll > delta: # last period for generation
        subsession.last_period = True
        #random.seed(a=roll, version=2)
        #subsession.payround = np.random.randint(1, nround)
        subsession.rfirst = bool(random.getrandbits(1))
        if gen >= last_gen_num:
            subsession.stop_session = True
        else:
            subsession.stop_session = False
    subsession.num_questions = len(C.history)
    subsession.last_gen_num = last_gen_num
    subsession.gen0 = gen0
    subsession.period_number = period  # increments period number
    subsession.current_gen = gen
    subsession.first_gen = gen == 1
    subsession.dice_roll = roll


def setIDs(group: Group): # give players generations and sides, carry forward variable values
    for p in group.get_players():
        p.gen = np.ceil(p.id_in_group / 2) + p.subsession.gen0
        p.side = p.id_in_group % 2 == 1
        if p.side:
            p.tag += "A"
        else:
            p.tag += "B"
        if p.round_number != 1:
            p.cum_payoff = p.in_round(p.round_number - 1).cum_payoff
            p.stage = p.in_round(p.round_number - 1).stage
            p.r_survey = p.in_round(p.round_number - 1).r_survey
            p.wait = p.in_round(p.round_number - 1).wait
            p.rfirst = p.in_round(p.round_number - 1).rfirst
            p.payround = p.in_round(p.round_number - 1).payround

#def pass_advice(player: Player):
#    for j in player.get_others_in_group():
#        if player.side == j.side and player.gen == j.gen + 1:
#            return player.g_advice

def opp(player: Player): # identify opponent
    for j in player.get_others_in_group():
        if player.gen == j.gen:
            return j

def pred(player: Player): # identify predecessor
    for j in player.get_others_in_group():
        if player.gen == j.gen + 1 and player.side == j.side:
            return j

def succ(player: Player): # identify successor
    for j in player.get_others_in_group():
        if player.gen == j.gen - 1 and player.side == j.side:
            return j

def sort_response(player: Player):
    N = player.subsession.num_questions
    if player.gen == 1:
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
            p.cum_payoff = p.payoff


        #p.participant.vars['pd_points'] += p.points
        #p.participant.payoff = round(p.participant.vars['pd_points'] * group.session.config['pd_conversion'], 2)
        #p.participant.vars['pd_dollars'] = p.participant.payoff
        # p.save()

# PAGES
class Initialize(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        setIDs(group)
        id = group.id_in_subsession
        for p in group.get_players():
            if p.gen == p.subsession.current_gen: # active generation
                p.stage = 0
                p.wait = False
            if p.gen < p.subsession.current_gen: # recall advice, survey generations increase 1 stage
                p.r_advice = p.in_round(p.round_number - 1).r_advice
                p.g_advice = p.in_round(p.round_number - 1).g_advice
                p.stage += 1
                if p.gen == 1:
                    p.r_survey = False
                else:
                    if p.stage < p.subsession.num_questions:
                        p.r_survey = p.rfirst
                    else:
                        p.r_survey = not p.rfirst
            if p.gen > p.subsession.current_gen:
                p.stage = -1
            if p.subsession.period_number == 1:
                p.participant.vars['match_history'] = {}
                p.participant.vars['interprets'] = list()
            # load saved advice
            if group.subsession.current_gen > 1: # load/update advice
                file = C.groupfile + str(id)
                with open(file, 'rb') as f:
                    advice1, advice2 = pickle.load(f)
                if p.stage == 0:
                    if p.side:
                        p.r_advice = advice1
                    else:
                        p.r_advice = advice2



class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        N = player.subsession.num_questions
        return (player.subsession.first_period and player.stage == 0) or player.stage == 1 or player.stage == N-1
    @staticmethod
    def vars_for_template(player: Player):
        tag = str(player.subsession.current_gen)
        if player.side:
            tag += 'A'
        else:
            tag += 'B'
        return {
            'first_period': player.subsession.first_period,
            'gen0': player.subsession.gen0,
            'wait': player.wait,
            'history': player.participant.vars['match_history'],
            'r_advice': player.r_advice,
            'gam_gen': player.subsession.current_gen,
            'gen': player.gen,
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
        tag = str(player.subsession.current_gen)
        if player.side:
            tag += 'A'
        else:
            tag += 'B'
        return {
            'interprets': player.participant.vars['interprets'],
            'first_gen': player.subsession.first_gen,
            'first_period': player.subsession.first_period,
            'history': player.participant.vars['match_history'],
            'delta':player.subsession.delta,
            'r_advice': player.r_advice,
            'gam_gen': player.subsession.current_gen,
            'CTAG':C.C_TAG,
            'DTAG':C.D_TAG,
            'gen': player.gen,
            'tag': tag,
            'round': player.subsession.round_number,
            'per': player.subsession.period_number,
        }

class Survey(Page):
    form_model = 'player'
    form_fields = ['interpret','clear']

    @staticmethod
    def is_displayed(player: Player):
        return player.stage > 0 and not player.wait

    @staticmethod
    def vars_for_template(player: Player):
        history = C.history
        N = player.subsession.num_questions
        question = (player.stage-1) % N
        r_survey = player.r_survey
        if r_survey:
            advice = player.r_advice # r_advice survey
        else:
            advice = player.g_advice # g_advice survey
        if question == N*2-2:
            player.wait = True
        if question == N-2 and (C.last_gen or player.gen == 1): # player done
            player.wait = True
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
            if p.stage > 0 and not p.wait: # active survey players
                hist = p.participant.vars['interprets']
                p.participant.vars['interprets'] = [hist, p.interpret]
            if p.stage > 0 and p.wait: # graduate inactive survey players once successor finishes r questions
                if p.gen < p.subsession.last_gen_num: # not last generation
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
        tag = str(player.subsession.current_gen)
        if player.side:
            tag += 'A'
        else:
            tag += 'B'
        match_list = []
        advice = player.r_advice
        return {
            'first_gen': player.subsession.first_gen,
            'first_period': player.subsession.first_period,
            'r_advice': advice,
            'history': player.participant.vars['match_history'],
            'match_list': match_list,
            'current_match': str(player.gen),
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
            r_advice = player.r_advice,
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
            first_period = False,
            history = player.participant.vars['match_history'],
            roll=player.subsession.dice_roll,
            delta=player.subsession.delta,
            r_advice=player.r_advice,
            first_gen= player.subsession.first_gen,
            per= player.subsession.period_number,
            stop=player.subsession.stop_session,)

# save progress
class Save(WaitPage):

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.last_period and not C.last_gen

    @staticmethod
    def after_all_players_arrive(group: Group):
        # save data for starting from next round
        gen = group.subsession.current_gen + 1
        with open(C.genfile, 'wb') as f:
            pickle.dump(gen, f)
        for p in group.get_players():
            if p.stage == 0:
                if p.side:
                    advice1 = p.g_advice
                else:
                    advice2 = p.g_advice
        id = group.id_in_subsession
        file = C.groupfile + str(id)
        # advice data
        if group.subsession.current_gen <= C.num_gen:
            with open(file, 'wb') as f:
                pickle.dump([advice1, advice2], f)
                f.close()


class EndOfGame(Page):
    timeout_seconds = 15
    @staticmethod
    def is_displayed(player: Player):
        return player.final_period

    @staticmethod
    def vars_for_template(player: Player):
        opponent = opp(player)
        # points for interpreting received advice
        if player.gen > player.subsession.gen0 + 1:
            rpoints = r_advice_score(player)
        else:
            rpoints = 0
        # points for interpreting given advice
        if player.gen < player.subsession.gen0 + C.num_gen:
            gpoints = g_advice_score(player)
        else:
            gpoints = 0
        ipoints = gpoints + rpoints # payoff from interpreting
        last_player = player.gen == player.subsession.last_gen_num
        return dict(
            opponent=opponent,
            same_choice=player.cooperate == opponent.cooperate,
            my_decision=player.field_display('cooperate'),
            opponent_decision=opponent.field_display('cooperate'),
            roll=player.subsession.dice_roll,
            r_advice=player.r_advice,
            payoff=player.cum_payoff + ipoints,
            gen=player.subsession.current_gen,
            numgen= C.num_gen,
            gpoints= gpoints,
            rpoints= rpoints,
            ipoints = ipoints,
            last = last_player,
            gen0=player.subsession.gen0,
            per=player.subsession.period_number,
            stop=player.subsession.stop_session,
        )

page_sequence = [Initialize,Introduction,
                 Decision, Survey, ResultsWaitPage, Results, EndOfMatch,
    #WaitingRoom
   Save, EndOfGame,]


#page_sequence = [Introduction, Decision, ResultsWaitPage, ResultsPage, WaitGroup, Results]
