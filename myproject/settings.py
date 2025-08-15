from os import environ

SESSION_CONFIGS = [
    dict(
        name='GPD',
        display_name="GPD",
        app_sequence=['GPD', 'payment_info'],
        num_demo_participants= 4, # num_groups*
        gen_end = False, # final generation
        dynasty_session = 1,
    ),
    dict(
        name='RPD',
        display_name="RPD",
        app_sequence=['RPD', 'payment_info'],
        num_demo_participants= 2, # num_groups*
        gen_end = False, # final generation
        dynasty_session = 1,
    ),
    dict(
        name='survey', app_sequence=['survey', 'payment_info'], num_demo_participants=1
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.10, participation_fee=14.00, doc=""
)

PARTICIPANT_FIELDS = ['tag','rpoints','rsurvey','gsurvey','g_advice','r_advice','match_history','match_payoffs']
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ROOMS = [
    dict(name='cess', display_name='CESS'),
]



ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
Here are some oTree games.
"""

SECRET_KEY = '{{ secret_key }}'

INSTALLED_APPS = ['otree']
