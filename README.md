# Sopel-Art
Sopel-Art is a port of the old deerkins project.  It allows users to produce beautiful ART in a web browser to display in an IRC channel.
The big differences between the original deerkins and this project are as follows:

* It's a sopel module (which means it's in Python now)
* It accepts new art via a RESTful API
* New art modifiers!

## Installation
You should add this module to sopel.  You can do this by adding the path to this module to your sopel config under `[core] extra`.
You can run the sopel with the config flag (-w) to configure the bot.  You will need to set up a web accessible page 
that will allow you to generate new art.  See the example.html for more information.

## Commands
* `.art` will print out a random art
* `.art <artname>` will print out a specific art.
* `.art <artname>|<modifiers>` will print out the modified art
* `.art |<modifiers>` will print out the a random modified art

## Modifiers
* d - divide
* f - shift, shifts each line of the art a bit
* i - invert, inverts the colors of the art
* m - mirror, mirror image
* n - unitinu the image
* r - reverse the image
* s - square
* u - upsidedown
* x - apply a bunch of random modifiers :)

## Demo
Artbutt can (at least now) be found at http://art.devhax.com/ and is the place where anyone can create art.  The bot it 
is attached to is named "Melvis" and is on irc.devhax.com.  You can see it in action in #art.
