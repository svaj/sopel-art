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
import numpy as np
from io import BytesIO
from sopel.config.types import StaticSection, ValidatedAttribute
from flask import Flask
from flask_cors import CORS
from flask_restless import APIManager
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from requests import get as http_get
from marshmallow import Schema, fields, post_load
from marshmallow.exceptions import ValidationError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, Integer, String, Text
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color


ART_TRIGGER = 'art'
app = Flask(__name__)
CORS(app)
local_bot = None
db = {}

Base = declarative_base()  # SA Base

irc_colors = {
    (211, 215, 207): 0,
    (46, 52, 54): 1,
    (52, 101, 164): 2,
    (78, 154, 6): 3,
    (204, 0, 0): 4,
    (143, 57, 2): 5,
    (92, 53, 102): 6,
    (206, 92, 0): 7,
    (196, 160, 0): 8,
    (115, 210, 22): 9,
    (17, 168, 121): 10,
    (88, 161, 157): 11,
    (87, 121, 158): 12,
    (160, 67, 101): 13,
    (85, 87, 83): 14,
    (136, 137, 133): 15
}

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

reverse_color_map = {
    1: ' ',
    0: 'A',
    2: 'B',
    3: 'C',
    4: 'D',
    5: 'E',
    6: 'F',
    7: 'G',
    8: 'H',
    9: 'I',
    10: 'J',
    11: 'K',
    12: 'L',
    13: 'M',
    14: 'N',
    15: 'O',
}


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
    the_art = False
    modifiers = ''

    if not cut_trigger:
        query = db.session.query(Art)
        row_count = int(query.count())
        the_art = query.offset(int(row_count * random.random())).first()
    else:
        # Attempt to get art & see about modifiers
        if '|' in cut_trigger:
            modifiers = cut_trigger[cut_trigger.index('|'):].strip()
            cut_trigger = cut_trigger[:cut_trigger.index('|')].strip()
            if cut_trigger == '':
                query = db.session.query(Art)
                row_count = int(query.count())
                the_art = query.offset(int(row_count * random.random())).first()
        if not the_art:
            the_art = db.session.query(Art).filter_by(art=cut_trigger).first()
    if the_art:
        print_art(bot, the_art, modifiers)
        db.session.commit()
    else:
        bot.say("No such art found! Create art at {}".format(bot.config.art.url))


def print_art(bot, current_art, modifiers=''):
    """
    Prints an art to irc using the supplied bot.
    :param bot: sopel bot.
    :param current_art: the art to print.
    :return: None.
    """
    current_art.display_count += 1
    kinskode = current_art.kinskode
    irccode = current_art.irccode
    if modifiers:
        print(kinskode)
        kinskode = apply_modifiers(kinskode, list(modifiers))
        print("--------------!!!-------------")
        print(kinskode)
        irccode = convert_kinskode_to_irccode(kinskode, 30, 30)
    for line in irccode.split('\n'):
        bot.stack = {}  # Get rid of our stack (avoid "..." messages)
        bot.say(line)
    bot.stack = {}
    bot.say("{} by {} (printed {} times now)".format(current_art.art, current_art.creator, current_art.display_count))


def convert_kinskode_to_irccode(art_text, max_lines=20, max_cols=30):
    """
    Converts "kinskode" art into IRC Codes (color codes, etc).
    :param art_text: The kinskode art.
    :return: The converted IRC code art.
    """
    global color_map
    c = chr(3)
    fill = '@'
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
        parsed += "{}\n".format(parsed_line)

    return parsed


def apply_modifiers(kinskode='', modifiers=None):
    """ Applies a list of modifiers to an art. """
    mod_map = {
        'i': 'invert',
        'm': 'mirror',
        'n': 'unitinu',
        'd': 'divide',
        'r': 'reverse',
        'u': 'upsidedown',
        's': 'square',
        'f': 'shift',
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
                kinskode = globals()[func](kinskode)
            except Exception as e:
                print(e)
                print("uh oh")
                pass
    return kinskode


def strtr(strng, replace):
    """ python implementation of strtr. """
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
    """ inverts colors of the art. """
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
    """ just upside-downs the art. """
    return '\n'.join(kinskode.split('\n')[::-1])


def modify_mirror(kinskode='', direction=0):
    """
    :param kinskode: art kinskode to modify
    :param direction: direction to mirror (mirror, unitinu, divide)
    :return: modified kinskode.
    """
    longest = max(kinskode.split('\n'), key=len)
    half = math.floor(len(longest) / 2)
    print("half is {}".format(half))
    if half < 1:
        return kinskode
    new_code = ''
    for line in kinskode.split('\n'):
        if direction == 0:
            new_code += modify_reverse(line)[:half].strip() + line[half:] + '\n'
        elif direction == 1:
            new_code += line[:half] + modify_reverse(line)[half:].strip() + '\n'
        else:
            new_code += modify_reverse(line)[half:].strip() + line[:half] + '\n'
    return new_code


def modify_unitinu(kinskode=''):
    """ UNITINU's the art. """
    return modify_mirror(kinskode, direction=1)


def modify_divide(kinskode=''):
    """ Divide the art."""
    return modify_mirror(kinskode, direction=2)


def modify_square(kinskode=''):
    """
    Squares an art.
    :param kinskode: art kinskode to square
    :return: squared kinskode
    """
    longest = max(kinskode.split('\n'), key=len)
    half = math.floor(len(longest) / 2)
    if half < 1:
        return kinskode
    c = 0
    lines = kinskode.split('\n')
    new_code = ''
    for line in lines:
        if c < math.floor(len(lines) / 2):
            new_code += line[:half] + line[half:] + '\n'
        else:
            new_code = line[:half] + line[half:] + '\n' + new_code

    return new_code


def modify_shift(kinskode=''):
    """
    Shifts an art.
    :param kinskode: art kinskode to square
    :return: squared kinskode
    """
    longest = max(kinskode.split('\n'), key=len)
    half = math.floor(len(longest) / 2)
    if half < 1:
        return kinskode
    lines = kinskode.split('\n')
    shift_amount = random.randint(1, len(lines[0]))
    beginning_pixels = lines[-1][:shift_amount]
    new_code = ''
    for line in lines:
        new_code += beginning_pixels + line[len(beginning_pixels):] + '\n'
        shift_amount += 1
        beginning_pixels = line[:shift_amount]
        if shift_amount >= len(line) - 1:
            shift_amount = 1
    return new_code


def modify_x(kinskode='', iteration=0):
    """Applies a random amount of modifiers """
    if iteration < 4:
        iteration += 1
    else:
        return kinskode

    mod_map = {
        'i': 'invert',
        'm': 'mirror',
        'n': 'unitinu',
        'd': 'divide',
        'r': 'reverse',
        'u': 'upsidedown',
        'f': 'shift',
        's': 'square'
    }
    for i in range(4, random.randrange(4, 10)):
        k, func_str = random.choice(list(mod_map.items()))
        func = 'modify_' + func_str
        try:
            kinskode = globals()[func](kinskode)
        except Exception as e:
            print(e)
            print("uh oh")
            pass
    if random.randint(0, 1) == 1:
        return modify_x(kinskode, iteration)

    return kinskode


def convert_image_to_kinskode(url=''):
    """ Downloads an image and converst to kinskode. """
    global irc_colors
    global reverse_color_map
    """ Given an image's url, convert it to kinskode as best as we can. """
    # Download image
    i = Image.open(BytesIO(http_get(url).content)).convert('RGBA')
    # resize to small
    w = 30
    h = 20
    size = w, h
    i.thumbnail(size)
    width, height = i.size
    # read it and set up our kinskode
    kinskode = ""
    colors = list(irc_colors.keys())
    arr = np.array(np.asarray(i).astype('float'))
    for line in arr:
        for pixel in line:
            closest_colors = sorted(colors, key=lambda color: img_distance(color, pixel))
            closest_color = closest_colors[0]
            kinskode += reverse_color_map[irc_colors[closest_color]]
        kinskode += "\n"
    return kinskode


@app.route('/convert')
def convert_image_endpoint():
    """ Endpoint to convert images to kinskode. """
    from flask import request
    if not request.args.get('url', False):
        return "Invalid URL parameter."
    return convert_image_to_kinskode(request.args.get('url', ''))


def img_distance(c1, c2):
    """ https://codebottle.io/code/1a4f8338/ """
    rgb1 = sRGBColor(c1[0], c1[1], c1[2])
    rgb2 = sRGBColor(c2[0], c2[1], c2[2])
    lab1 = convert_color(rgb1, LabColor)
    lab2 = convert_color(rgb2, LabColor)
    (r1, g1, b1) = lab1.lab_l, lab1.lab_a, lab1.lab_b
    (r2, g2, b2) = lab2.lab_l, lab2.lab_a, lab2.lab_b

    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
