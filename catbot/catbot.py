#!python3
# -*- coding: utf-8 -*-

import discord
import random
import datetime
import dice
import os
import asyncio
import importlib
import catbot.botbase as base
import catbot.macromodule as macro
import catbot.aimodule as aimodule, catbot.catbotcli as catbotcli, catbot.dogapi as dogapi, catbot.catapi as catapi
from catbot.cbmessage import CatbotMessage
from catbot.ai.vision import CatbotVision, HasImageRule, CatbotVisionHistory
from catbot.serverconfig import CatbotConfig
from catbot.comm.meowmeowprotocol import MeowMeowProtocol

VERSION = "2.1.3"

"""
TODO

- new type of rule CountRule - greater/less/eq/..., chars/words
- poll feature (use embed)

"""

TOKEN_FILE_NAME = "discord_token"
DISABLE_AI_FILE_NAME = "disable_ai"
CMD = "$cat$"

CURR = 0
DISABLE_AI = os.path.exists(DISABLE_AI_FILE_NAME)

BOT = discord.Client()
CLI = catbotcli.CatCLI()
AIM = aimodule.AIModule()
CAT_VISION = CatbotVision(enabled=not DISABLE_AI)

LASTDAY = None


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
    e = discord.Embed(title="Available commands", color=base.COLOR_MAIN)
    e.set_thumbnail(url=str(cmsg.bot.user.avatar_url))
    embed_ln(e, "!catbot quiet true/false", "Enables or disables quiet mode.")
    embed_ln(e, "!catbot prefix PREFIX", "Changes command prefix to PREFIX.")
    embed_ln(e, cp + "macros", "List defined macros.")
    embed_ln(e, cp + "define MACRO_NAME CONTENT", "Define a new macro.")
    embed_ln(e, cp + "undefine MACRO_NAME", "Undefine macro.")
    embed_ln(e, "/MACRO_NAME [MACRO_NAME] ...", "Convert macro name to its content. Macros can be chained.")
    embed_ln(e, cp + "roll DICE_DEF", "Roll the dice. Syntax can be found here: https://pypi.org/project/dice/ \nExample: !roll 3d5+1")
    embed_ln(e, cp + "a TEXT", "Send text to the AI module.")
    embed_ln(e, cp + "introspect", "Get bot state.")
    embed_ln(e, cp + "cat", "Cat.")
    embed_ln(e, cp + "dog", "Like cat, but dog.")
    embed_ln(e, cp + "vision history", "Show log of vision events with timestamps, processing time and confidence.")
    embed_ln(e, cp + "help", "Display this help text.")
    e.set_footer(text=cmsg.bot_name + " version " + VERSION)
    await cmsg.embed(e)


def set_quiet_mode(config, server_id, value):
    config["quiet_mode"] = value
    CatbotConfig.commit_config(server_id, config)


# TODO probs refactor and move somewhere else (cli?)
async def catbot_command(cmsg):
    # system commands
    if len(cmsg.words) == 1:
        await get_help_message(cmsg)
        return
    elif len(cmsg.words) >= 2:
        # explicit catbot help
        if cmsg.words[1].lower() in ["hlep", "help"]:
            await get_help_message(cmsg)
            return
        # prefix change
        elif cmsg.words[1].lower() == "prefix":
            start_ind = cmsg.raw_lower.index("prefix") + len("prefix") + 1
            prefix = cmsg.raw_lower[start_ind:]
            if prefix == "":
                prefix = "!"
            cmsg.config["command_prefix"] = prefix
            CatbotConfig.commit_config(cmsg.server_id, cmsg.config)
            await cmsg.respond("Command prefix changed to \"{}\"".format(cmsg.config["command_prefix"]))
            return
        # quiet mode change
        elif cmsg.words[1].lower() == "quiet":
            start_ind = cmsg.raw_lower.index("quiet") + len("quiet") + 1
            quietstr = cmsg.raw_lower[start_ind:].lower().strip()
            if quietstr in ["true", "1", "yes"]:
                quiet_mode = True
            elif quietstr in ["false", "0", "no"]:
                quiet_mode = False
            else:
                await cmsg.respond("Invalid quiet mode value, specify true or false")
                return
            set_quiet_mode(cmsg.config, cmsg.server_id, quiet_mode)
            await cmsg.respond("Quiet mode " + ("enabled." if quiet_mode else "disabled."))


async def get_introspection_result(cmsg):
    aim_accessible = AIM.test()
    e = discord.Embed(title="Internal state", color=base.COLOR_ORANGE, description="(debug information)")
    e.set_thumbnail(url=str(cmsg.bot.user.avatar_url))
    embed_ln(e, "Name", str(cmsg.bot_name))
    embed_ln(e, "Nickname", str(cmsg.bot_nickname))
    embed_ln(e, "Version", VERSION)
    embed_ln(e, "AIM accessible", str(aim_accessible))
    embed_ln(e, "Cat vision enabled", str(CAT_VISION.enabled))
    embed_ln(e, "Command prefix", str(cmsg.config.get("command_prefix", "!")))
    embed_ln(e, "Quiet mode", str(cmsg.config.get("quiet_mode", False)))
    embed_ln(e, "Meowmeow protocol channel", str(cmsg.config.get("mmp_channel", None)))
    e.set_footer(text=cmsg.bot_name + " version " + VERSION)
    await cmsg.embed(e)


def rewrite_command_prefix(raw_content, prefix):
    raw_lower = raw_content.lower()
    prefix_lower = prefix.lower()
    raw_lower_stripped = raw_lower.strip()
    if raw_lower_stripped.startswith(prefix_lower) and not raw_lower_stripped.startswith("!catbot"):
        start_ind = raw_lower.index(prefix_lower)
        return CMD + raw_content[start_ind + len(prefix_lower):]
    else:
        return raw_content


@BOT.event
async def on_member_join(member):
    print("Member joined:", member.display_name)
    if member.bot:
        system_channel = member.guild.system_channel
        if system_channel is not None:
            await system_channel.send("Hello {}! {}".format(member.display_name, base.EMOJI_BLOBCATWAVE))
            await system_channel.send("For better compatibility with more bots, you can set quiet mode by issuing "
                                      "the following command:\n`!catbot quiet 1`")


@BOT.event
async def on_guild_join(guild):
    print("Joined a new server:", guild.name)
    system_channel = guild.system_channel
    if system_channel is not None:
        await system_channel.send("HI! Am catbot.")
        bot_members = list(filter(lambda member: member.bot and member != BOT.user, guild.members))
        if len(bot_members) > 0:
            await asyncio.sleep(2)
            await system_channel.send("More bots! " + base.EMOJI_BLOBCATSHOCKED)
            for bot in bot_members:
                await system_channel.send("Hi {}!".format(bot.display_name))
            await system_channel.send(base.EMOJI_BLOBCATWAVE)
            await system_channel.send("\nI will go into quiet mode now to prevent conflicts with my other robotic " +
                                      "frens. \nIf you wish to disable quiet mode, issue the following command:" +
                                      "\n`!catbot quiet false`" +
                                      "\n(But be warned! This can have terrible consequences. " +
                                      "Potentially the end of the world.)" +
                                      "\n\nI'm also setting my command prefix to be \"!cb\". To change it, you can " +
                                      "use `!catbot prefix PREFIX`"
                                      "\n\nFor more information, type `!catbot help`")
            # change settings
            server_id = str(guild.id)
            config = CatbotConfig.get_config(server_id)
            config["command_prefix"] = "!cb"
            # set_quiet_mode will also commit the config
            set_quiet_mode(config, str(server_id), True)


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


class IsQuietRule(base.Rule):

    def __init__(self):
        super().__init__(None, base.Rule.CUSTOM, base.NOP_MODULE)

    def check(self, cmsg):
        return cmsg.config.get("quiet_mode", False)


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
        base.Rule(CMD + "vision history", base.Rule.CONTAINS_ALL, CatbotVisionHistory()),
        HasImageRule(CAT_VISION),

        # identity rule
        base.RuleOp.rules_and().rules(
            base.AsyncFuncCall(identity),
            base.Rule("mentioned", base.Rule.FLAGS_ALL, None),
            base.Rule(["question", "inquiry", "indirect_inquiry"], base.Rule.FLAGS_ONE_OF, None),
            base.Rule("who are you", base.Rule.CONTAINS_ALL, None)
        ),

        # reaction rules
        base.RuleOp.rules_and().rules(
            base.AsyncFuncCall(wise_response),
            base.Rule("mentioned", base.Rule.FLAGS_ALL, None),
            base.Rule(["question", "inquiry", "indirect_inquiry"], base.Rule.FLAGS_ONE_OF, None)
        ),

        # quiet mode abort point
        IsQuietRule(),

        # no mention rules
        base.Rule(["morning", "myrming"], base.Rule.FLAGS_ONE_OF, base.SimpleReaction(base.EMOJI_SUN)),
        base.Rule("night", base.Rule.FLAGS_ALL, base.SimpleReaction(base.EMOJI_MOON)),
        base.Rule(["greeting", "farewell"], base.Rule.FLAGS_ONE_OF, base.SimpleReaction(base.EMOJI_WAVE)),

        BeepBoopRule(base.AsyncFuncCall(beep_boop))
    ]
}


def run():
    if DISABLE_AI:
        print("AI disabled - file \"{}\" is present".format(DISABLE_AI_FILE_NAME))
    BOT.run(load_token())
