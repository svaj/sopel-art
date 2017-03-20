# coding=utf8

import MySQLdb # TODO: Make this Sql alchemy!
import sopel.module
from sopel.config.types import StaticSection, ValidatedAttribute
from flask import Flask, abort
import threading  # This is so we can start flask in a thread. :D

app = Flask(__name__)
local_bot = None


class ArtSection(StaticSection):
    """ Setup what our config keys look like. """
    db_host = ValidatedAttribute('db_host', default="localhost")
    """The MySQL host for storing art."""

    db_user = ValidatedAttribute('db_user', default="sopel_art")
    """The MySQL user for storing art."""

    db_pass = ValidatedAttribute('db_pass')
    """The MySQL pass for storing art."""

    db_name = ValidatedAttribute('db_name', default="sopel_art")
    """The MySQL database name for storing art."""


def setup(bot):
    """Starts up Flask to allow POSTs to add new arts. """
    global local_bot
    global app
    bot.config.define_section('art', ArtSection)
    local_bot = bot
    threading.Thread(target=app.run,
        args=(),
        kwargs={'host': '0.0.0.0', 'port': 62333},
    ).start()


def configure(config):
    """ Configure the bot! """

    """Set up our config values. """
    config.define_section('art', ArtSection, validate=False)
    config.art.configure_setting('db_host', 'What is the MySQL hostname for storing art?')
    config.art.configure_setting('db_name', 'What is the MySQL database name for storing art?')
    config.art.configure_setting('db_user', 'What is the MySQL username for storing art?')
    config.art.configure_setting('db_pass', 'What is the MySQL password for storing art?')

    """ Initializes the art database. """
    db = MySQLdb.connect(host=config.art.db_host,
                         user=config.art.db_user,
                         passwd=config.art.db_pass,
                         db=config.art.db_name)
    cur = db.cursor()
    # Create art table
    cur.execute("CREATE TABLE IF NOT EXISTS `art` ( \
                `id` int(11) NOT NULL auto_increment, \
                `date` datetime NOT NULL, \
                `creator` text NOT NULL, \
                `art` text NOT NULL, \
                `kinskode` text NOT NULL, \
                `irccode` text NOT NULL, \
                `display_count` int NOT NULL DEFAULT 0, \
                PRIMARY KEY  (`id`) \
                ) ENGINE=MyISAM  DEFAULT CHARSET=utf8mb4")
    # Insert an art :D
    db.commit()
    db.close()

@sopel.module.commands('art')
def art(bot, trigger):
    """ Prints an art from the db"""
    bot.say('Not yet buddy.')


