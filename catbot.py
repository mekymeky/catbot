#!python3
# -*- coding: utf-8 -*-
import discord
import random
import datetime
import macromodule as macro
import catbotcli
import dice
import importlib
import aimodule
import catapi
import dogapi
import botbase as base
from cbmessage import CatbotMessage

VERSION = "2.0.2"

CURR = 0

BOT = discord.Client()
CLI = catbotcli.CatCLI()
AIM = aimodule.AIModule()

LASTDAY = None

TOKEN_FILE_NAME = "discord_token"


def __reload_cli__():
    global CLI
    importlib.reload(catbotcli)
    CLI = catbotcli.CatCLI()


def roll(a, b=None):
    if b is None:
        b = a
        a = 1
    return random.randint(a, b)


def special_msg_deserved():
    global LASTDAY
    today = datetime.datetime.now().day
    if LASTDAY is None:
        if roll(100) == 1:
            LASTDAY = today
            return True
    elif LASTDAY != today:
        LASTDAY = None  # week-long fail safety
        if roll(100) == 1:
            LASTDAY = today
            return True


@BOT.event
async def on_ready():
    print('Logged in as')
    print(BOT.user.name)
    print(BOT.user.id)
    print('------')


def guess():
    r = random.randint(0, 9)

    if r == 0:
        return "Definitely."
    elif r <= 2:
        return "Yes."
    elif r <= 4:
        return "No."
    elif r <= 5:
        return "Nope."
    elif r <= 7:
        return "Perhaps."
    elif r <= 8:
        return "Maybe."
    elif r == 9:
        return "mlem"


def embed_ln(embed, name, value, inline=False):
    embed.add_field(name=name, value=value, inline=inline)


async def get_help_message(cmsg):
    e = discord.Embed(title="Available commands", color=0x5bad8b)
    e.set_thumbnail(url=str(cmsg.bot.user.avatar_url))
    embed_ln(e, "!macros", "List defined macros.")
    embed_ln(e, "!define MACRO_NAME CONTENT", "Define a new macro.")
    embed_ln(e, "!undefine MACRO_NAME", "Undefine macro.")
    embed_ln(e, "/MACRO_NAME [MACRO_NAME] ...", "Convert macro name to its content. Macros can be chained.")
    embed_ln(e, "!roll DICE_DEF", "Roll the dice. Syntax can be found here: https://pypi.org/project/dice/ \nExample: !roll 3d5+1")
    embed_ln(e, "!a TEXT", "Send text to the AI module.")
    embed_ln(e, "!introspect", "Get bot state.")
    embed_ln(e, "!cat", "Cat.")
    embed_ln(e, "!dog", "Like cat, but dog.")
    embed_ln(e, "!help", "Display this help text.")
    e.set_footer(text=cmsg.bot_name + " version " + VERSION)
    await cmsg.embed(e)


async def get_introspection_result(cmsg):
    aim_accessible = AIM.test()
    e = discord.Embed(title="Internal state", color=0xf3c24a, description="(Not yet implemented)")
    e.set_thumbnail(url=str(cmsg.bot.user.avatar_url))
    embed_ln(e, "name", str(cmsg.bot_name))
    embed_ln(e, "nickname", str(cmsg.bot_nickname))
    embed_ln(e, "version", VERSION)
    embed_ln(e, "AIM accessible", str(aim_accessible))
    e.set_footer(text=cmsg.bot_name + " version " + VERSION)
    await cmsg.embed(e)


@BOT.event
async def on_message(message):
    au = str(message.author)
    cmsg = CatbotMessage(BOT, message)
    rn = roll(1000)
    print("rn:", rn)
    print(cmsg.raw)

    # Ignore bot's own messages
    if message.author == BOT.user:
        return

    # Process message using available ruleset
    action = base.Action(base.Action.CONTINUE)
    while action.type == base.Action.CONTINUE:
        action = base.NO_MESSAGE_ACTION
        for rule in RULES["global"]:
            base.LOGGER.debug("Checking rule: ", rule)
            if rule.check(cmsg):
                base.LOGGER.debug("Running module")
                action = await rule.module.run(cmsg)

                if action is None or not isinstance(action, base.Action):
                    action = base.NO_MESSAGE_ACTION
                if action.message:
                    await cmsg.respond(action.message)
                if action.reaction:
                    await cmsg.react(action.reaction)
                if rule.exclusive:
                    base.LOGGER.debug("Exclusive rule, breaking execution")
                    break

    # Log debug string
    base.LOGGER.debug(cmsg.dbgstring())

    # Admin commands
    if au == "Meky#8888":
        await admin_commands(cmsg)

    # Cookie reaction
    if rn == 1 and message.author != BOT.user:
        await message.add_reaction(base.EMOJI_COOKIE)


async def admin_commands(cmsg):
    if "!dbg" in cmsg.raw_lower:
        await cmsg.respond(cmsg.dbgstring())
    elif "!reloadcli" in cmsg.raw_lower:
        try:
            __reload_cli__()
            resp = CLI.reload_message()
        except Exception as err:
            resp = "`" + str(err) + "`"
        await cmsg.respond(resp)


def dice_roll(cmsg):
    rollmsg = str(dice.roll(cmsg.raw[6::]))
    if "[" in rollmsg and "]" in rollmsg:
        rollmsg = rollmsg[1:-1]
    return rollmsg


async def wise_response(cmsg):
    await cmsg.react(base.EMOJI_THINK)
    await cmsg.sleep(1)
    await cmsg.respond(guess())


# legacy macro processing function, to be refactored to Module
async def process_macro(cmsg):
    chain = cmsg.raw.split(" ")
    emptychain = True
    for mtext in chain:
        resp = macro.run(cmsg, mtext)
        if not (resp == ""):
            emptychain = False
            await cmsg.respond(resp)
    if not emptychain:
        await cmsg.delete()
    return base.NO_MESSAGE_ACTION


async def ai_process(cmsg):
    response = AIM.process(cmsg.raw[3::])
    await cmsg.respond(response)


def load_token():
    try:
        token_file = open(TOKEN_FILE_NAME, "r")
        data = token_file.read()
        token_file.close()
        return data.strip()
    except Exception as ex:
        base.LOGGER.error(ex)
        raise RuntimeError("Failed to load token file, please check if it exists: " + str(TOKEN_FILE_NAME))


async def beep_boop(cmsg):
    remapping = {"o": "e", "O": "E", "e": "o", "E": "O", "i": "o", "I": "O"}
    response = ""
    for char in cmsg.raw:
        if char in remapping:
            response += remapping[char]
        else:
            response += char
    await cmsg.respond(response)


class BeepBoopRule(base.Rule):

    def __init__(self, module):
        super().__init__(None, base.Rule.CUSTOM, module)

    def check(self, cmsg):
        char_filter = ["b", "l", "i", "e", "o", "p"]
        filtered = ""
        for char in cmsg.raw_lower:
            if 97 <= ord(char) <= 122:
                if char not in char_filter:
                    return False
                filtered += char
                if len(filtered) > 5:
                    return False
        return filtered in ["beep", "boop", "bep", "bop", "bip", "bepp", "bopp", "blep", "blop", "blip",
                            "blepp", "blopp", "blipp"]


RULES = {
    "global": [
        # main, exclusive rules
        base.Rule(["!help", "!hlep"], base.Rule.STARTS_WITH, base.AsyncFuncCall(get_help_message)),
        base.Rule("!introspect", base.Rule.STARTS_WITH, base.AsyncFuncCall(get_introspection_result)),
        base.Rule("!cli", base.Rule.STARTS_WITH, base.Module("Catbot CLI", base.Module.NATIVE, handler=CLI.handle)),
        base.Rule("!define ", base.Rule.STARTS_WITH, base.FuncCall(macro.define)),
        base.Rule("!undefine ", base.Rule.STARTS_WITH, base.FuncCall(macro.undefine)),
        base.Rule("!macros", base.Rule.STARTS_WITH, base.StrFuncCall(macro.listmacros)),
        base.Rule("/", base.Rule.STARTS_WITH, base.AsyncFuncCall(process_macro)),
        base.Rule("!a ", base.Rule.STARTS_WITH, base.AsyncFuncCall(ai_process)),
        base.Rule("!roll ", base.Rule.STARTS_WITH, base.StrFuncCall(dice_roll)),
        base.Rule(["!cat", "!kitte", "!kitty", "!meow", "!kat"], base.Rule.STARTS_WITH, catapi.CatApi()),
        base.Rule(["!dog", "!woof", "!bark", "!bork"], base.Rule.STARTS_WITH, dogapi.DogApi()),

        # reaction rules
        base.RuleOp.rules_and().rules(
            base.AsyncFuncCall(wise_response),
            base.Rule("mentioned", base.Rule.FLAGS_ALL, None),
            base.Rule(["question", "inquiry" "indirect_inquiry"], base.Rule.FLAGS_ONE_OF, None)
        ),
        base.Rule(["morning", "myrming"], base.Rule.FLAGS_ONE_OF, base.SimpleReaction(base.EMOJI_SUN)),
        base.Rule("night", base.Rule.FLAGS_ALL, base.SimpleReaction(base.EMOJI_MOON)),
        base.Rule(["greeting", "farewell"], base.Rule.FLAGS_ONE_OF, base.SimpleReaction(base.EMOJI_WAVE)),

        BeepBoopRule(base.AsyncFuncCall(beep_boop))
    ]
}

BOT.run(load_token())
