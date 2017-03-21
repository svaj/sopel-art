# coding=utf8


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, DateTime, Integer, String, Text
import sopel.module
from sopel.config.types import StaticSection, ValidatedAttribute
from flask import Flask, abort
import random
import threading  # This is so we can start flask in a thread. :D


ART_TRIGGER = 'art'
app = Flask(__name__)
local_bot = None

Base = declarative_base()  # SA Base
engine = {}
DBSession = {}


class Art(Base):
    __tablename__ = 'art'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    creator = Column(String(250), nullable=False)
    art = Column(Text, nullable=False)
    kinskode = Column(Text, nullable=False)
    irccode = Column(Text, nullable=False)
    display_count = Column(Integer, nullable=False)


class ArtSection(StaticSection):
    """ Setup what our config keys look like. """
    db_engine = ValidatedAttribute('db_engine', default="sqlite:///sopel_art.db")
    """The MySQL host for storing art."""

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
    bot.config.define_section('art', ArtSection)
    local_bot = bot
    port = bot.config.art.port
    threading.Thread(target=app.run,
        args=(),
        kwargs={'host': '0.0.0.0', 'port': port},
    ).start()
    print("Listening for arts on {}".format(port))
    engine = create_engine(bot.config.art.db_engine)
    Session = sessionmaker(bind=engine)
    DBSession = Session()


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
    cut_trigger = trigger[len(ART_TRIGGER):].strip()
    art = False
    if not cut_trigger:
        query = DBSession.query(Art)
        rowCount = int(query.count())
        art = query.offset(int(rowCount * random.random())).first()
    else:
        # Attempt to get art
        art = DBSession.query(Art).filter_by(art=cut_trigger).first()
    if art:
        print_art(bot, art)
        DBSession.add(art)
        DBSession.commit()
    else:
        bot.say("No such art found! Create art at {}".format(bot.config.art.url))


def print_art(bot, art):
    """
    Prints an art to irc using the supplied bot.
    :param bot: sopel bot.
    :param art: the art to print.
    :return: None.
    """
    art.display_count += 1
    for line in art.irccode.split('\n'):
        bot.say(line)
    bot.say("{} by {} (printed {} times now)".format(art.art, art.creator, art.display_count))
