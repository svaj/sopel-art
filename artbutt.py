# coding=utf8
"""
Sopel-Art!

https://github.com/svaj/artbutt

A beautiful sopel plugin that allows users to create and display deliciously aesthetic IRC art!

This was originally a PHP bot thing, named deerkins, https://github.com/worldeggplant/deerkins.  However,
no one in their right mind runs a PHP irc bot.

"""

import datetime
import random
import threading  # This is so we can start flask in a thread. :D
import sopel.module
from sopel.config.types import StaticSection, ValidatedAttribute
from flask import Flask
from flask_restless import APIManager
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, post_load
from marshmallow.exceptions import ValidationError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, Integer, String, Text


ART_TRIGGER = 'art'
app = Flask(__name__)
local_bot = None
db = {}

Base = declarative_base()  # SA Base


class Art(Base):
    """ Our Art model.  Beautiful. """
    __tablename__ = 'art'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    creator = Column(String(250), nullable=False)
    art = Column(Text, nullable=False, unique=True)
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
    """ This prepares new art before adding it to the db. """
    data['irccode'] = convert_kinskode_to_irccode(data['kinskode'])
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


def convert_kinskode_to_irccode(art_text):
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
    for line in art_text.split('\n'):
        for char in line:
            char = char.upper()
            color = color_map[char]
            if prev_char == char:
                parsed += fill
            else:
                parsed += "{}{},{}{}".format(c, str(color).zfill(2), str(color).zfill(2), fill)
        parsed += "\n"
    return parsed
