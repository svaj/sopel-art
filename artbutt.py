# coding=utf8
"""
Sopel-Art!

https://github.com/svaj/sopel-art

A beautiful sopel plugin that allows users to create and display deliciously aesthetic IRC art!

This was originally a PHP bot thing, named deerkins, https://github.com/worldeggplant/deerkins.  However,
no one in their right mind runs a PHP irc bot.

"""

import datetime
import math
import random
import threading  # This is so we can start flask in a thread. :D
import sopel.module
from sopel.config.types import StaticSection, ValidatedAttribute
from flask import Flask
from flask_cors import CORS
from flask_restless import APIManager
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, post_load
from marshmallow.exceptions import ValidationError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, Integer, String, Text


ART_TRIGGER = 'art'
app = Flask(__name__)
CORS(app)
local_bot = None
db = {}

Base = declarative_base()  # SA Base


class Art(Base):
    """ Our Art model.  Beautiful. """
    __tablename__ = 'art'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    creator = Column(String(250), nullable=False)
    art = Column(String(250), nullable=False, unique=True)
    kinskode = Column(Text, nullable=False)
    irccode = Column(Text, nullable=False, default='')
    display_count = Column(Integer, nullable=False, default=0)


class ArtSchema(Schema):
    """ A Marshmallow schema for Art. """
    id = fields.Int(dump_only=True)
    creator = fields.Str()
    date = fields.Date()
    art = fields.Str()
    kinskode = fields.Str()
    irccode = fields.Str(load_only=True)

    @post_load
    def make_art(self, data):
        """MAKE ART"""
        return Art(**data)


class ArtSection(StaticSection):
    """ Setup what our config keys look like. """
    db_engine = ValidatedAttribute('db_engine', default="sqlite:///sopel_art.db")
    """The full sqlalchemy uri for the database, e.g. sqlite:///sopel_art.db or postgresql://user:pass@localhost:5432/artdb"""

    port = ValidatedAttribute('port', default="5309")
    """The art API port."""

    url = ValidatedAttribute('port', default="http://art.devhax.com/")
    """The art creation site's full URL."""

    max_lines = ValidatedAttribute('max_lines', default=20)
    """ The maximum number of lines an art can take up. """

    max_cols = ValidatedAttribute('max_lines', default=30)
    """ The maximum number of columns an art can take up. """


art_schema = ArtSchema()


def art_serializer(instance):
    """ Use Marshmallow for serializing a single instance. """
    return art_schema.dump(instance).data


def art_deserializer(data):
    """ This lets us use Marshmallow to load new arts. """
    global db
    d = art_schema.load(data)
    if db.session.query(Art).filter(Art.art == d.data.art).first() is not None:
        raise ValidationError(message='ART IS NOT UNIQUE.', field_names=['art'], fields=d.data.art)
    return d.data


def art_after_get_many(result=None, search_params=None, **kw):
    """ This lets us use Marshmallow to serialize our collection. """
    result['objects'] = [art_serializer(obj) for obj in result['objects']]


def art_before_insert(data=None, **kw):
    global local_bot
    """ This prepares new art before adding it to the db. """
    data['irccode'] = convert_kinskode_to_irccode(data['kinskode'], local_bot.config.art.max_lines, local_bot.config.art.max_cols)
    data['date'] = datetime.datetime.utcnow().isoformat()


def setup(bot):
    """Starts up Flask to allow POSTs to add new arts. """
    global local_bot
    global app
    global db
    bot.config.define_section('art', ArtSection)
    local_bot = bot
    port = bot.config.art.port
    app.config['SQLALCHEMY_DATABASE_URI'] = bot.config.art.db_engine
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db = SQLAlchemy(app)
    Base.metadata.create_all(bind=db.engine)
    db.init_app(app)
    db.create_all()
    manager = APIManager(app, flask_sqlalchemy_db=db)
    manager.create_api(
        Art,
        methods=['GET', 'POST'],
        max_results_per_page=50,
        results_per_page=50,
        serializer=art_serializer,
        deserializer=art_deserializer,
        validation_exceptions=[ValidationError],
        preprocessors={
            'POST': [art_before_insert]
        },
        postprocessors={
            'GET_MANY': [art_after_get_many]
        })
    threading.Thread(
        target=app.run,
        args=(),
        kwargs={'host': '0.0.0.0', 'port': port},
    ).start()
    print("Listening for art on {}".format(port))


def configure(config):
    """ Configure the bot! """

    """Set up our config values. """
    config.define_section('art', ArtSection, validate=False)
    config.art.configure_setting('db_engine', 'What is the SQLAlchemy engine for storing art?')

    config.define_section('art', ArtSection, validate=False)
    config.art.configure_setting('port', 'What is the port the art API will listen on?')

    config.define_section('art', ArtSection, validate=False)
    config.art.configure_setting('url', 'What is the URL of your art creation site?')

    """ Initializes the art database. """
    engine = create_engine(config.art.db_engine)
    # Create art table
    Base.metadata.create_all(engine)


@sopel.module.commands(ART_TRIGGER)
def art(bot, trigger):
    """
    Either grabs a random art, or an art with a name of the trigger and then prints the art,
    incrementing its display count.
    :param bot: bot.
    :param trigger: The trigger executing the command ".art <artname>"
    :return: None.
    """
    global db
    global ART_TRIGGER
    cut_trigger = trigger[len(ART_TRIGGER)+1:].strip()
    print("wat")
    the_art = False
    if not cut_trigger:
        query = db.session.query(Art)
        row_count = int(query.count())
        the_art = query.offset(int(row_count * random.random())).first()
    else:
        # Attempt to get art
        the_art = db.session.query(Art).filter_by(art=cut_trigger).first()
    if the_art:
        print_art(bot, the_art)
        db.session.commit()
    else:
        bot.say("No such art found! Create art at {}".format(bot.config.art.url))


def print_art(bot, current_art):
    """
    Prints an art to irc using the supplied bot.
    :param bot: sopel bot.
    :param current_art: the art to print.
    :return: None.
    """
    current_art.display_count += 1
    for line in current_art.irccode.split('\n'):
        bot.say(line)
        bot.stack = {}  # Get rid of our stack (avoid "..." messages)
    bot.say("{} by {} (printed {} times now)".format(current_art.art, current_art.creator, current_art.display_count))


def convert_kinskode_to_irccode(art_text, max_lines=20, max_cols=30):
    """
    Converts "kinskode" art into IRC Codes (color codes, etc).
    :param art_text: The kinskode art.
    :return: The converted IRC code art.
    """
    c = chr(3)
    fill = '@'
    color_map = {
        ' ': 1,
        'A': 0,
        'B': 2,
        'C': 3,
        'D': 4,
        'E': 5,
        'F': 6,
        'G': 7,
        'H': 8,
        'I': 9,
        'J': 10,
        'K': 11,
        'L': 12,
        'M': 13,
        'N': 14,
        'O': 15,
        '_': 00
    }
    prev_char = ''
    parsed = ''
    for line in art_text.split('\n')[:max_lines]:
        parsed_line = ''
        for char in line:
            char = char.upper()
            color = color_map[char]
            if prev_char == char:
                parsed_line += fill
            else:
                parsed_line += "{}{},{}{}".format(c, str(color).zfill(2), str(color).zfill(2), fill)
        parsed += "{}\n".format(parsed_line[:max_cols])

    return parsed


def apply_modifiers(kinskode='', modifiers=None):
    mod_map = {
        'i': 'invert',
        'm': 'mirror',
        'n': 'unitinu',
        'd': 'divide',
        'r': 'reverse',
        'u': 'upsidedown',
        's': 'square',
        'f': 'flip',
        'x': 'x'
    }
    unique_mods = set(modifiers)
    if 'x' in unique_mods:
        unique_mods = {'x'}
    for mod in unique_mods:
        if mod not in mod_map:
            pass
        else:
            func = 'modify_' + mod_map[mod]
            try:
                kinskode = locals()[func](kinskode)
            except Exception:
                pass
    return kinskode


def strtr(strng, replace):
    buffer = []
    i, n = 0, len(strng)
    while i < n:
        match = False
        for s, r in replace.items():
            if strng[i:len(s)+i] == s:
                buffer.append(r)
                i = i + len(s)
                match = True
                break
        if not match:
            buffer.append(strng[i])
            i = i + 1
    return ''.join(buffer)


def modify_invert(kinskode=''):
    invert_map = {
        ' ': 'A',
        'A': ' ',
        'B': 'H',
        'C': 'M',
        'D': 'J',
        'E': 'K',
        'F': 'I',
        'G': 'L',
        'H': 'B',
        'I': 'M',
        'J': 'D',
        'K': 'E',
        'L': 'G',  # H ?
        'M': 'C',  # I ?
        'N': 'O',
        'O': 'N',
        '_': ' '
    }
    return strtr(kinskode.upper(), invert_map)


def modify_reverse(kinskode=''):
    """ reverses kinskode. """
    new_code = ''
    for line in kinskode.split('\n'):
        new_code += line[::-1] + '\n'  # reversed
    return new_code


def modify_upsidedown(kinskode=''):
    return kinskode.split('\n')[::-1].join('\n')


def modify_mirror(kinskode='', direction=0):

    half = math.floor(max(kinskode.split('\n'), key=len))
    if half < 1:
        return kinskode
    new_code = ''
    for line in kinskode.split('\n'):
        if direction == 0:
            new_code += modify_reverse(line)[:half].trim() + line[half:] + '\n'
        elif direction == 1:
            new_code += line[:half] + modify_reverse(line)[half:].trim() + '\n'
        else:
            new_code += modify_reverse(line)[half:].trim() + line[:half] + '\n'
    return new_code


def modify_unitinu(kinskode=''):
    return modify_mirror(kinskode, direction=1)


def modify_divide(kinskode=''):
    return modify_mirror(kinskode, direction=2)


def modify_square(kinskode=''):
    return kinskode


def modify_flip(kinskode=''):
    return kinskode


def modify_x(kinskode=''):
    return kinskode
