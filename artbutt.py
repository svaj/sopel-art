# coding=utf8
"""
Sopel-Art!

https://github.com/svaj/artbutt

A beautiful sopel plugin that allows users to create and display deliciously aesthetic IRC art!

This was originally a PHP bot thing, named deerkins, https://github.com/worldeggplant/deerkins.  However,
no one in their right mind runs a PHP irc bot.

"""

import random
import threading  # This is so we can start flask in a thread. :D
import sopel.module
from sopel.config.types import StaticSection, ValidatedAttribute
from flask import Flask, abort, jsonify
from flask_restless import APIManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, DateTime, Integer, String, Text


ART_TRIGGER = 'art'
app = Flask(__name__)
local_bot = None

Base = declarative_base()  # SA Base
engine = {}
DBSession = {}
db = {}

class Art(Base):
    __tablename__ = 'art'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    creator = Column(String(250), nullable=False)
    art = Column(Text, nullable=False, unique=True)
    kinskode = Column(Text, nullable=False)
    irccode = Column(Text, nullable=False)
    display_count = Column(Integer, nullable=False)


class ArtSection(StaticSection):
    """ Setup what our config keys look like. """
    db_engine = ValidatedAttribute('db_engine', default="sqlite:///sopel_art.db")
    """The full sqlalchemy uri for the database, e.g. sqlite:///sopel_art.db or postgresql://user:pass@localhost:5432/artdb"""

    port = ValidatedAttribute('port', default="5309")
    """The art API port."""

    url = ValidatedAttribute('port', default="http://art.devhax.com/")
    """The art creation site's full URL."""


def setup(bot):
    """Starts up Flask to allow POSTs to add new arts. """
    global local_bot
    global app
    global engine
    global DBSession
    global db
    bot.config.define_section('art', ArtSection)
    local_bot = bot
    port = bot.config.art.port
    app.config['SQLALCHEMY_DATABASE_URI'] = bot.config.art.db_engine
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    engine = create_engine(bot.config.art.db_engine)
    Session = sessionmaker(bind=engine)
    DBSession = Session()

    db = SQLAlchemy(app)
    manager = APIManager(app, flask_sqlalchemy_db=db)
    manager.create_api(Art, methods=['GET', 'POST'])

    threading.Thread(target=app.run,
        args=(),
        kwargs={'host': '0.0.0.0', 'port': port},
    ).start()
    print("Listening for arts on {}".format(port))

    # Create API endpoints, which will be available at /api/<tablename> by
    # default. Allowed HTTP methods can be specified as well.


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
    global DBSession
    global ART_TRIGGER
    cut_trigger = trigger[len(ART_TRIGGER)+1:].strip()
    the_art = False
    if not cut_trigger:
        query = DBSession.query(Art)
        row_count = int(query.count())
        the_art = query.offset(int(row_count * random.random())).first()
    else:
        # Attempt to get art
        the_art = DBSession.query(Art).filter_by(art=cut_trigger).first()
    if the_art:
        print_art(bot, the_art)
        DBSession.commit()
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


@app.route("/artz", methods=['GET'])
def get_art():
    """ List the arts. """
    return jsonify({'art': Art.query.all()})


@app.route("/artz", methods=['POST'])
def add_art():
    """ Add an art. """
    if not request.json or not 'name' in request.json:
        abort(400)
    print("HA HA HA")
