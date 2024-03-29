from otree.api import *
import numpy as np
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
    num_gen = 2
    num_dynasty = 3
    PLAYERS_PER_GROUP = num_gen*2
    delta = 50
    gamma = 1
    inactive_color = ["#FAE5CB", "#CBE6FA"]
    active_color = ["SandyBrown","LightSkyBlue"]
    history_color = active_color
    outcome_color = ["Orange","DeepSkyBlue"]
    button_color = outcome_color
    hover_color = ["#FE9900","#00C4FE"]
    genfile = 'gen'
    groupfile = 'advice'
    history = [{},
                #{'P1': {'period': '1', 'name_opp_action': C_TAG, 'opp_cooperate': True}},
                #{'P1': {'period': '1', 'name_opp_action': D_TAG, 'opp_cooperate': False}},
                {'P1': {'period': '1', 'name_opp_action': D_TAG, 'opp_cooperate': False},
                 'P2': {'period': '2', 'name_opp_action': C_TAG, 'opp_cooperate': True}}
                    ] # questions for advice survey


class Subsession(BaseSubsession):
    dice_roll = models.IntegerField(initial=-10)
    gen_number = models.IntegerField(initial=-10)  # which generation this round corresponds to
    first_period = models.BooleanField(initial=True)  # True if it is the first period of a match
    last_period = models.BooleanField(initial=False)  # True if it is the last period of a match
    period_number = models.IntegerField(initial=1)
    current_gen = models.IntegerField(initial=1)
    num_questions = models.IntegerField(initial = 0)
    delta = models.IntegerField(initial = C.delta)
    stop_session = models.BooleanField(initial = False)
    dynasty_session = models.IntegerField(initial = -1)


class Group(BaseGroup):
    number = models.IntegerField()
    dynasty = models.IntegerField(initial = -1)

class Player(BasePlayer):
    # Game fields
    final_period = models.BooleanField(initial = False) # ready to receive payoff, leave experiment
    action = models.StringField(initial=C.D_TAG)
    cooperate = models.BooleanField(
        choices=[[True, C.C_TAG], [False, C.D_TAG]],
        doc="""This player's decision""",
        widget=widgets.RadioSelect,
        initial= False,
    )
    session_gen = models.IntegerField(initial = 1)
    gen = models.IntegerField(initial = 1)
    # advice
    ancestor_advice = models.LongStringField(label="Advice to you", default="")
    ancestor_participant_id = models.IntegerField(default=0)
    g_advice = models.LongStringField(initial = '',label="Advice:")
    # ID fields
    first_gen = models.BooleanField(initial = False)
    session_end = models.BooleanField(initial = False)
    last_gen = models.BooleanField(initial = False)
    side = models.BooleanField(initial = False)
    stage = models.IntegerField(initial=-1)
    tag = models.StringField(initial = "")
    # Survey fields
    rfirst = models.BooleanField(initial = False)
    r_survey = models.BooleanField(initial = True) # interpreting received advice
    interpret = models.BooleanField()
    clear = models.BooleanField(label="Does the advice clearly indicate what to do in this scenario?")
    g_responses = models.StringField(initial = '')
    rpoints = models.CurrencyField(initial = 0)
    gpoints = models.CurrencyField(initial = 0)


# FUNCTIONS
def creating_session(subsession: Subsession):
    if len(subsession.get_groups())>C.num_dynasty:
        ValueError("Too many groups")
    nround = subsession.round_number # current round
    ## ROLL Round incrementing

    # draw random number for each round
    seed = random.seed(a=None, version=2)
    random.seed(a=seed, version=2)
    dice_rolls = np.random.randint(1, 100, C.NUM_ROUNDS+1).tolist()
    subsession.session.vars['dice_rolls'] = dice_rolls

    if subsession.session.config['gen_end']:
        delta = 1-(1-C.delta)/(1+C.gamma)
    else:
        delta = C.delta

    roll = dice_rolls[nround]
    if roll > delta: # last period for generation
        subsession.last_period = True
        if subsession.current_gen >= C.num_gen:
            subsession.stop_session = True
        else:
            subsession.stop_session = False


    ## player advice/incrementing
    # initialize roles and draw advice
    players = subsession.get_players()
    subsession.dynasty_session = subsession.session.config['dynasty_session']
    if nround == 1:
        subsession.period_number = 1
        subsession.current_gen = 1
        try:
            ancestors = get_ancestor_players(subsession.dynasty_session)
        except:
            ancestors = []
        finally:
            dynasties = list(range(0, C.num_dynasty))
            dynasty_ages = list(range(0, C.num_dynasty))
            print(dynasties)
            num_groups = len(subsession.get_groups())
            print(dynasties)
            for dynasty in dynasties:
                print(dynasty)
                dynasty_ancestors = [ancestor for ancestor in ancestors if ancestor.dynasty == dynasty]
                try:
                    age = max([ancestor.gen for ancestor in dynasty_ancestors]) # generation of dynasty
                except:
                    age = 0
                dynasty_ages[dynasty] = age
                print("Dynasty ages " +str(dynasty_ages))
                print("Dynasties " +str(dynasties))
            print("Removing "+str(C.num_dynasty-num_groups)+" dynasties")
            print(dynasties)
            for n in range(num_groups,C.num_dynasty):
                long_dynasties = [i for i in dynasties if dynasty_ages[i] == max(dynasty_ages)] # maximum length dynasties
                dynasties.remove(min(long_dynasties)) # remove first dynasty reaching this value
                dynasty_ages.remove(max(dynasty_ages))
                print(dynasties)
            ancestor_players = [ancestor for ancestor in ancestors if ancestor.dynasty in dynasties]
        create_database_tables()
        #subsession.group_randomly()
        # randomly assign groups, generations, dynasty
        num = 0
        for group in subsession.get_groups():
            gens = []
            group.number = num
            print("Group:"+str(group.number))
            group.dynasty = dynasties[num]
            group_gen = dynasty_ages[num]
            print("Generation:"+str(group_gen))
            print("Dynasty:"+str(group.dynasty))
            for i in range(1,C.num_gen+1):
                gens = gens + [i, i]
            random.shuffle(gens)
            num += 1
            group_players = group.get_players()
            for p, gen in zip(group_players, gens):
                p.session_gen = gen
            for gen in range(1,C.num_gen+1):
                gen_players = [player for player in group_players if player.session_gen == gen]
                random.shuffle(gen_players)
                sides = [True, False]
                for p, side in zip(gen_players, sides):
                    p.side = side
                    p.session_end = (p.session_gen == C.num_gen)
            for p in group_players:
                p.participant.vars['interprets'] = []
                p.participant.vars['g_advice'] = ''
                p.participant.vars['match_history'] = {}
                p.participant.vars['done'] = False
                p.rfirst = bool(random.getrandbits(1))
            if group_gen > 0:
                print(ancestor_players)
                ancestor_options = [ancestor for ancestor in ancestor_players if (ancestor.dynasty == group.dynasty and ancestor.gen == group_gen)]
                for p in group_players:
                    if p.session_gen == 1:
                        print("Group dynasty:"+str(group.dynasty))
                        ancestor = random.choice(ancestor_options)
                        ancestor_options.remove(ancestor)
                        p.gen = ancestor.gen + 1
                        get_tag(p)
                        p.ancestor_participant_id = ancestor.participant_id
                        if ancestor.g_advice == '':
                            ValueError("Advice not passed")
                        p.participant.vars['asurvey'] = string_to_bool(ancestor.g_survey)
                        if p.participant.vars['asurvey'] == []:
                            ValueError("asurvey empty")
                        p.participant.vars['r_advice'] = ancestor.g_advice
            else: # first group in dynasty
                for p in group_players:
                    p.first_gen = (p.session_gen == 1)
                    if p.first_gen:
                        p.rfirst = False
                        p.gen = p.session_gen
                        get_tag(p)
                        p.participant.vars['asurvey'] = []
                        p.participant.vars['r_advice'] = ''
            for p in players: # identify later generations
                p.stage = 0
                if p.session_gen > 1:
                    p.stage = -1
                    p.gen = get_predecessor(p).gen + 1
                    get_tag(p)
    # continue advice/ increment player attributes
    subsession.num_questions = len(C.history)
    if nround > 1:
        for g in subsession.get_groups():
            g.dynasty = g.in_round(nround - 1).dynasty
            g.number = g.in_round(nround - 1).number
        # increment session generation attributes
        if subsession.in_round(nround - 1).last_period:  # new generation
            period = 1
            gen = subsession.in_round(nround - 1).current_gen + 1
            subsession.first_period = True
        else:  # same generation
            period = subsession.in_round(nround - 1).period_number + 1
            gen = subsession.in_round(nround - 1).current_gen
            subsession.first_period = False
        subsession.period_number = period  # increments period number
        subsession.current_gen = gen

        for p in players:
            if p.session_end and p.session.config['gen_end']:
                p.last_gen = True
            p.side = p.in_round(nround - 1).side
            p.gen = p.in_round(nround - 1).gen
            get_tag(p)
            p.session_gen = p.in_round(nround - 1).session_gen
            p.session_end = (p.session_gen == C.num_gen)
            p.first_gen = p.in_round(nround - 1).first_gen
        #active_players = [player for player in players if player.session_gen == subsession.current_gen]
            p.participant.vars['wait'] = False
            p.rfirst = p.in_round(p.round_number - 1).rfirst
            if p.session_gen == subsession.current_gen: # Pass advice in later generations (inheritance already random from role)
                p.stage = 0
            if p.session_gen < p.subsession.current_gen:  # if retired, recall advice, survey generations, increment stage
                p.stage = p.in_round(p.round_number - 1).stage + 1
                if p.stage <= p.subsession.num_questions:
                    p.r_survey = p.rfirst
                else:
                    p.r_survey = not p.rfirst
            if p.session_gen > p.subsession.current_gen:
                p.stage = -1
                p.participant.vars['wait'] = True
    subsession.delta = delta
    subsession.dice_roll = roll

def get_tag(player: Player): # identify opponent
    side =player.side
    tag = str(player.gen)
    if side:
        tag += 'A'
    else:
        tag += 'B'
    player.tag = tag
def successor_tag(player: Player): # identify opponent
    side =player.side
    tag = str(player.gen + 1)
    if side:
        tag += 'A'
    else:
        tag += 'B'
    return(tag)

def predecessor_tag(player: Player): # identify opponent
    side =player.side
    tag = str(player.gen - 1)
    if side:
        tag += 'A'
    else:
        tag += 'B'
    return(tag)

def get_opponent(player: Player): # identify opponent
    for j in player.get_others_in_group():
        if player.session_gen == j.session_gen:
            return j

def get_predecessor(player: Player): # identify predecessor
    for j in player.get_others_in_group():
        if player.session_gen == j.session_gen + 1 and player.side == j.side:
            return j

def get_successor(player: Player): # identify successor
    for j in player.get_others_in_group():
        if player.session_gen == j.session_gen - 1 and player.side == j.side:
            return j

def bool_to_string(bool_list): # converts boolean lists to strings to pass between players
    string_list = [str(int(elem)) for elem in bool_list]
    return ','.join(string_list)

def string_to_bool(comma_string): # converts comma strings to boolean list
    return [bool(int(elem)) for elem in comma_string.split(',')]

def sort_gresponse(player: Player):
    N = player.subsession.num_questions
    if player.first_gen == 1:
        return player.participant.vars['interprets'][0: N]
    if player.rfirst:
        return player.participant.vars['interprets'][N:2 * N]
    else:
        return player.participant.vars['interprets'][0: N]

def sort_rresponse(player: Player):
    N = player.subsession.num_questions
    if player.first_gen == 1:
        ValueError("No received advice")
    if player.last_gen:
        return player.participant.vars['interprets'][0: N]
    if player.rfirst:
        return player.participant.vars['interprets'][0: N]
    else:
        return player.participant.vars['interprets'][N:2 * N]

def r_advice_score(player: Player): # score points for received advice
    predecessor_resp = player.participant.vars['asurvey']
    r_responses = sort_rresponse(player)
    num_correct = len([i for i in range(0,len(r_responses)) if r_responses[i] == predecessor_resp [i]]) # count matching interpretations
    return num_correct*C.PAYOFF_I

def set_payoffs(group: Group):
    for p in group.get_players():
        if p.stage == 0:
            j = get_opponent(p)
            payoff_matrix = {
               (False, True): C.PAYOFF_DC,
                (True, True): C.PAYOFF_CC,
                (False, False): C.PAYOFF_DD,
                (True, False): C.PAYOFF_CD,
            }
            p.payoff = payoff_matrix[(p.cooperate,j.cooperate)]
        if p.stage > 0 and not p.participant.vars['done']:
            p.payoff = 0


        #p.participant.vars['pd_points'] += p.points
        #p.participant.payoff = round(p.participant.vars['pd_points'] * group.session.config['pd_conversion'], 2)
        #p.participant.vars['pd_dollars'] = p.participant.payoff
        # p.save()

# PAGES
            #if p.session_gen > 1:
             #   ancestor = get_predecessor(p)
              #  p.ancestor_session_id = ancestor.session_id
               # p.ancestor_participant_id = ancestor.participant_id
                #if p.stage == 0:
                 #   p.participant.vars['r_advice'] = ancestor.participant.vars['g_advice']
                #if p.stage > 0:
                 #   p.participant.vars['asurvey'] = ancestor.g_responses



class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        N = player.subsession.num_questions
        return (player.subsession.first_period and player.stage == 0) or player.stage == 1 or (player.stage == N+1 and not player.participant.vars['wait'])
    @staticmethod
    def vars_for_template(player: Player):
        opp = get_opponent(player)
        return {
            'first_period': player.subsession.first_period,
            'wait': player.participant.vars['wait'],
            'r_advice': player.participant.vars['r_advice'],
            'gam_gen': player.subsession.current_gen,
            'gen': player.session_gen,
            'first_gen': player.first_gen,
            'delta':player.subsession.delta,
            'pred_tag': predecessor_tag(player),
            'tag': player.tag,
            'opp_tag': opp.tag,
            'succ_tag': successor_tag(player),
            'succ_opp_tag':successor_tag(opp),
            'stage':player.stage,
            'survey_instr': not (player.stage == 0),
            'rsurvey':player.r_survey,
            'round': player.subsession.round_number,
            'per': player.subsession.period_number,
            'last_gen':C.num_gen,
            'end2':(player.session_gen == C.num_gen),
            'end':player.session_end,
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
        #player.participant.vars['match_history']['P' + p.subsession.period_number] = {}
        return {
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'Dbutton_color': C.button_color[False],
            'Cbutton_color': C.button_color[True],
            'Dbutton_hover': C.hover_color[False],
            'Cbutton_hover': C.hover_color[True],
            'session_end':player.session_end,
            'group': player.group,
            'period': player.subsession.period_number,
            'interprets': player.participant.vars['interprets'],
            'asurvey': player.participant.vars['asurvey'],
            'first_gen': player.first_gen,
            'first_period': player.subsession.first_period,
            'history': player.participant.vars['match_history'],
            'delta':player.subsession.delta,
            'r_advice': player.participant.vars['r_advice'],
            'gam_gen': player.subsession.current_gen,
            'CTAG':C.C_TAG,
            'DTAG':C.D_TAG,
            'gen': player.session_gen,
            'pred_tag': predecessor_tag(player),
            'tag': player.tag,
            'opp_tag':get_opponent(player).tag,
            'round': player.subsession.round_number,
            'per': player.subsession.period_number,
            'session':player.session_id,
        }

class Survey(Page):
    form_model = 'player'
    form_fields = ['interpret']#,'clear']

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
            active_tag = player.tag
            opp_tag = get_opponent(player).tag
        else:
            advice = player.participant.vars['g_advice'] # g_advice survey
            active_tag = successor_tag(player)
            opp_tag = successor_tag(get_opponent(player))
        if player.first_gen or (player.session.config['gen_end'] and player.session_end):
            num_q = N
        else:
            num_q =2*N
        if player.stage == num_q:
            player.participant.vars['wait'] = True
        historyq = history[question]
        player.g_advice = player.participant.vars['g_advice']
        return {
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'Dbutton_color': C.button_color[False],
            'Cbutton_color': C.button_color[True],
            'Dbutton_hover': C.hover_color[False],
            'Cbutton_hover': C.hover_color[True],
            'advice': advice,
            'tag':player.tag,
            'active_tag':active_tag,
            'active_opp_tag':opp_tag,
            'pred_tag': predecessor_tag(player),
            'succ_tag': successor_tag(player),
            'first_gen': player.first_gen,
            'gadvice': player.g_advice,
            'r': r_survey,
            'round': len(historyq)+1,
            'asurvey': player.participant.vars['asurvey'],
            'rfirst': player.rfirst,
            'history':historyq,
            'first':historyq == {},
            'delta':player.subsession.delta,
            'CTAG':C.C_TAG,
            'DTAG':C.D_TAG,
            'stage':player.stage,
            'q':question,
            'num_q':num_q
        }

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars['interprets'].append(player.interpret)

class ResultsWaitPage(WaitPage):
    template_name = 'prisoner/ResultsWaitPage.html'
    @staticmethod
    def after_all_players_arrive(group: Group):
        set_payoffs(group)
        period_number = str(group.subsession.period_number)
        N = group.subsession.num_questions
        for p in group.get_players():
            if p.participant.vars['done']:
                continue
            j = get_opponent(p)
            if p.stage < 0:
                continue
            if p.stage == 0: # active players
                if p.cooperate:
                    p.action = C.C_TAG
                if j.cooperate:
                    j.action = C.C_TAG
                p.participant.vars['match_history']['P' + period_number] = {
                        'period': period_number,
                        'cooperate':p.cooperate,
                        'name_action': p.action,
                        'opp_cooperate':j.cooperate,
                        'name_opp_action': j.action
                    }
                if p.subsession.last_period and p.session_gen>1:
                    predecessor = get_predecessor(p)
                    predecessor.payoff += p.payoff
                continue
            # SURVEY CALCULATIONS
            # calculate Gdone = predecssor done given advice survey
            num_question = 2*N
            if p.session_gen > 1:
                predecessor = get_predecessor(p)
                if predecessor.rfirst:
                    Gdone = (predecessor.stage >= 2*N)
                else:
                    Gdone = (predecessor.stage >= N)
            else: # session_gen == 1
                Gdone = True
                if p.first_gen:
                    num_question = N
                    p.rpoints = 0
            if not p.first_gen:
                # has receiver advice
                # calculate Rdone, if current player finished received advice survey
                if p.rfirst:
                    Rdone = (p.stage >= N)
                else:
                    Rdone = (p.stage >= 2*N)
                if Rdone and Gdone:
                    if p.session_gen > 1:
                        p.participant.vars['asurvey'] = sort_gresponse(predecessor)
                    # full responses to both surveys, calculate
                    p.rpoints = r_advice_score(p)
                    if p.session_gen > 1:
                        predecessor.gpoints = p.rpoints
                        predecessor.final_period = predecessor.participant.vars['wait']
            if p.session_end:
                p.gpoints = 0
                if p.session.config['gen_end']:
                    num_question = N
                    p.g_responses = ''
                if p.stage >= num_question:# last gen done when survey done
                    p.final_period = True
                    p.subsession.stop_session = True
        for p in group.get_players():
            if p.final_period and not p.participant.vars['done']:
                p.payoff += p.gpoints + p.rpoints # payoff from interpreting



    @staticmethod
    def vars_for_template(player: Player):
        advice = player.participant.vars['r_advice']
        return {
            'history_Ccolor': "style=\"background-color:"+C.history_color[True]+"\"",
            'history_Dcolor': "style=\"background-color:"+C.history_color[False]+"\"",
            'Dbutton_color': C.active_color[False],
            'Cbutton_color': C.active_color[True],
            'my_color':"style=\"background:"+C.inactive_color[player.cooperate]+";\"",
            'my_decision':player.cooperate,
            'first_gen': player.first_gen,
            'asurvey':player.participant.vars['asurvey'],
            'survey':player.participant.vars['interprets'],
            'period': player.subsession.period_number,
            'final': player.final_period,
            'stage': player.stage,
            'end': player.session_end,
            'history': player.participant.vars['match_history'],
            'first_period': player.subsession.period_number==1,
            'r_advice': advice,
            'current_match': str(player.session_gen),
            'tag': player.tag,
            'pred_tag': predecessor_tag(player),
            'per': player.subsession.period_number,
            'opp_tag': get_opponent(player).tag,
        }



class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.stage == 0

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        return dict(
            opponent=opponent,
            same_choice=player.cooperate == opponent.cooperate,
            period = player.subsession.period_number,
            my_decision=player.cooperate,
            opp_decision=opponent.cooperate,
            roll = player.subsession.dice_roll,
            history = player.participant.vars['match_history'],
            history_Ccolor = "style=\"background-color:"+C.history_color[True]+"\"",
            history_Dcolor = "style=\"background-color:"+C.history_color[False]+"\"",
            Dbutton_color= C.active_color[False],
            Cbutton_color= C.active_color[True],
            my_color="style=\"background:"+C.inactive_color[player.cooperate]+";\"",
            opp_color="style=\"background:"+C.inactive_color[opponent.cooperate]+";\"",
            outcome_color="style=\"background:"+C.outcome_color[opponent.cooperate]+";\"",
            tag = player.tag,
            opp_tag = get_opponent(player).tag,
            pred_tag = predecessor_tag(player),
            first_gen= player.first_gen,
            last_per=player.subsession.last_period,
            delta=player.subsession.delta,
            first_period = False,
            r_advice = player.participant.vars['r_advice'],
            g_advice=player.participant.vars['g_advice'],
            per= player.subsession.period_number,
            opp = get_opponent(player),
            stage = player.stage,)

    @staticmethod
    def before_next_page(player, timeout_happened):
        if not player.subsession.last_period:
            player.payoff = 0


# give advice
class EndOfMatch(Page):
    form_model = 'player'
    form_fields = ['g_advice']

    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.last_period and player.stage == 0 and not player.session.config['gen_end']

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        #player.in_all_rounds().g_advice = player.g_advice
        player.participant.vars['last_round'] = player.subsession.round_number
        return dict(
            history_Ccolor = "style=\"background-color:"+C.history_color[True]+"\"",
            history_Dcolor = "style=\"background-color:"+C.history_color[False]+"\"",
            Dbutton_color= C.active_color[False],
            Cbutton_color= C.active_color[True],
            opponent=opponent,
            tag = player.tag,
            opp_tag = get_opponent(player).tag,
            succ_tag= successor_tag(player),
            succ_opp_tag= successor_tag(get_opponent(player)),
            pred_tag = predecessor_tag(player),
            opp_succ_tag= successor_tag(get_opponent(player)),
            sessionid=player.session.id,
            same_choice=player.cooperate == opponent.cooperate,
            my_decision=player.field_display('cooperate'),
            opponent_decision=opponent.field_display('cooperate'),
            first_period = False,
            history = player.participant.vars['match_history'],
            roll=player.subsession.dice_roll,
            delta=player.subsession.delta,
            r_advice=player.participant.vars['r_advice'],
            first_gen= player.first_gen,
            per= player.subsession.period_number,)


    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars['g_advice'] = player.g_advice



class SaveLocal(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return player.subsession.last_period and not player.session.config['gen_end']

    @staticmethod
    def after_all_players_arrive(group: Group):
        for p in group.get_players():
            if not p.session_end:
                successor = get_successor(p)
                successor.ancestor_participant_id = p.participant_id
                successor.participant.vars['r_advice'] = p.participant.vars['g_advice']

class SaveSession(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return player.final_period and player.session_end

    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        player.g_advice = player.participant.vars['g_advice']
        player.g_responses = bool_to_string(sort_gresponse(player))
        add_player_history(player)


class EndOfGame(Page):
    #timeout_seconds = 30
    @staticmethod
    def is_displayed(player: Player):
        return player.final_period and not player.participant.vars['done']

    @staticmethod
    def vars_for_template(player: Player):
        opponent = get_opponent(player)
        player.participant.vars['done'] = True
        # points for interpreting received advice
        return dict(
            asurvey =player.participant.vars['asurvey'],
            opp_tag = get_opponent(player).tag,
            tag = player.tag,
            pred_tag = predecessor_tag(player),
            succ_tag= successor_tag(player),
            opp_succ_tag= successor_tag(get_opponent(player)),
            asurvey2 =player.participant.vars['interprets'],
            opponent=opponent,
            same_choice=player.cooperate == opponent.cooperate,
            my_decision=player.field_display('cooperate'),
            opponent_decision=opponent.field_display('cooperate'),
            roll=player.subsession.dice_roll,
            r_advice=player.participant.vars['r_advice'],
            payoff=player.participant.payoff,
            end=player.session_end,
            final = player.final_period,
            gen=player.session_gen,
            session_continue = not player.subsession.stop_session,
            current_gen=player.subsession.current_gen,
            gpoints= player.gpoints,
            rpoints= player.rpoints,
            dynasty = player.group.dynasty,
            last = (player.session_end and not player.session.config['gen_end']),
            per=player.subsession.period_number,
            session=player.session_id,
        )


page_sequence = [#Introduction,
                 Decision, #Survey,
                 ResultsWaitPage,
                  Results, EndOfMatch,
   SaveLocal,SaveSession,EndOfGame]


#page_sequence = [Introduction, Decision, ResultsWaitPage, ResultsPage, WaitGroup, Results]
