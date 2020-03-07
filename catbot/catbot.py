#!python3
# -*- coding: utf-8 -*-

import discord
import random
import datetime
import dice
import importlib
import catbot.botbase as base
import catbot.macromodule as macro
import catbot.aimodule as aimodule, catbot.catbotcli as catbotcli, catbot.dogapi as dogapi, catbot.catapi as catapi
from catbot.cbmessage import CatbotMessage
from catbot.ai.vision import CatbotVision, HasImageRule
from catbot.serverconfig import CatbotConfig
from catbot.comm.meowmeowprotocol import MeowMeowProtocol

VERSION = "2.1.1"

"""
TODO

- new type of rule CountRule - greater/less/eq/..., chars/words
- poll feature (use embed)

"""

CURR = 0

BOT = discord.Client()
CLI = catbotcli.CatCLI()
AIM = aimodule.AIModule()
CAT_VISION = CatbotVision(enabled=True)

LASTDAY = None

TOKEN_FILE_NAME = "discord_token"
CMD = "$cat$"


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
    cp = cmsg.command_prefix
    e = discord.Embed(title="Available commands", color=0x5bad8b)
    e.set_thumbnail(url=str(cmsg.bot.user.avatar_url))
    embed_ln(e, cp + "macros", "List defined macros.")
    embed_ln(e, cp + "define MACRO_NAME CONTENT", "Define a new macro.")
    embed_ln(e, cp + "undefine MACRO_NAME", "Undefine macro.")
    embed_ln(e, "/MACRO_NAME [MACRO_NAME] ...", "Convert macro name to its content. Macros can be chained.")
    embed_ln(e, cp + "roll DICE_DEF", "Roll the dice. Syntax can be found here: https://pypi.org/project/dice/ \nExample: !roll 3d5+1")
    embed_ln(e, cp + "a TEXT", "Send text to the AI module.")
    embed_ln(e, cp + "introspect", "Get bot state.")
    embed_ln(e, cp + "cat", "Cat.")
    embed_ln(e, cp + "dog", "Like cat, but dog.")
    embed_ln(e, cp + "help", "Display this help text.")
    e.set_footer(text=cmsg.bot_name + " version " + VERSION)
    await cmsg.embed(e)


async def catbot_command(cmsg):
    print(cmsg.words)
    if len(cmsg.words) == 1:
        await get_help_message(cmsg)
        return
    elif len(cmsg.words) == 2:
        if cmsg.words[1].lower() in ["hlep", "help"]:
            await get_help_message(cmsg)
            return
    elif len(cmsg.words) >= 3:
        print("OK")
        if cmsg.words[1].lower() == "prefix":
            print("OK-OK")
            start_ind = cmsg.raw_lower.index("prefix") + len("prefix") + 1
            cmsg.config["command_prefix"] = cmsg.raw_lower[start_ind:]
            CatbotConfig.commit_config(cmsg.server_id, cmsg.config)
            await cmsg.respond("Command prefix changed to \"{}\"".format(cmsg.config["command_prefix"]))
            return


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


def rewrite_command_prefix(raw_content, prefix):
    raw_lower = raw_content.lower()
    prefix_lower = prefix.lower()
    if raw_lower.strip().startswith(prefix_lower):
        start_ind = raw_lower.index(prefix_lower)
        return CMD + raw_content[start_ind + len(prefix_lower):]
    else:
        return raw_content


@BOT.event
async def on_message(message):
    au = str(message.author)
    config = CatbotConfig.get_config(str(message.guild.id))
    print("Retrieved cfg", config)

    # Ignore bot's own messages
    if message.author == BOT.user:
        return

    # Rewrite commands according to server config
    command_prefix = config.get("command_prefix", "!")
    message.content = rewrite_command_prefix(message.content, command_prefix)

    # print message content
    try:
        print(message.content)
    except Exception as ex:
        print(ex)

    cmsg = CatbotMessage(BOT, message, config, VERSION)
    rn = roll(1000)
    print("rn:", rn)

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


async def identity(cmsg):
    await cmsg.send_file("", discord.File("resources/bot.png"))
    await cmsg.respond("Bot.")


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
        base.Rule(base.EMOJI_CAT, base.Rule.STARTS_WITH, MeowMeowProtocol()),
        base.Rule(["!catbot", CMD + "catbot"], base.Rule.STARTS_WITH, base.AsyncFuncCall(catbot_command)),
        base.Rule([CMD + "help", CMD + "hlep"], base.Rule.STARTS_WITH, base.AsyncFuncCall(get_help_message)),
        base.Rule(CMD + "introspect", base.Rule.STARTS_WITH, base.AsyncFuncCall(get_introspection_result)),
        base.Rule(CMD + "cli", base.Rule.STARTS_WITH, base.Module("Catbot CLI", base.Module.NATIVE, handler=CLI.handle)),
        base.Rule(CMD + "define ", base.Rule.STARTS_WITH, base.FuncCall(macro.define)),
        base.Rule(CMD + "undefine ", base.Rule.STARTS_WITH, base.FuncCall(macro.undefine)),
        base.Rule(CMD + "macros", base.Rule.STARTS_WITH, base.StrFuncCall(macro.listmacros)),
        base.Rule("/", base.Rule.STARTS_WITH, base.AsyncFuncCall(process_macro)),
        base.Rule(CMD + "a ", base.Rule.STARTS_WITH, base.AsyncFuncCall(ai_process)),
        base.Rule(CMD + "roll ", base.Rule.STARTS_WITH, base.StrFuncCall(dice_roll)),
        base.Rule([CMD + "cat", CMD + "kitte", CMD + "kitty", CMD + "meow", CMD + "kat"], base.Rule.STARTS_WITH, catapi.CatApi()),
        base.Rule([CMD + "dog", CMD + "woof", CMD + "bark", CMD + "bork"], base.Rule.STARTS_WITH, dogapi.DogApi()),

        # vision
        HasImageRule(CAT_VISION),

        # identity rule
        base.RuleOp.rules_and().rules(
            base.AsyncFuncCall(identity),
            base.Rule("mentioned", base.Rule.FLAGS_ALL, None),
            base.Rule(["question", "inquiry" "indirect_inquiry"], base.Rule.FLAGS_ONE_OF, None),
            base.Rule("who are you", base.Rule.CONTAINS_ALL, None)
        ),

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


def run():
    BOT.run(load_token())
