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
import botbase as base
from cbmessage import CatbotMessage

VERSION = "2.0.0"

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


def get_help_message(cmsg):
    result = "```"
    result += "Available commands:\n"
    result += "!macros\n"
    result += "!define ...\n"
    result += "!undefine ...\n"
    result += "!roll ...\n"
    result += "!a ...\n"
    result += "!introspect\n"
    result += "!help\n"
    result += "```"
    return result


def get_introspection_result(cmsg):
    aim_accessible = AIM.test()
    result = "```"
    result += BOT.user.name + " version: " + VERSION + "\n"
    result += "\n"
    result += "AIM accessible: " + str(aim_accessible) + "\n"
    result += "```"
    return result


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
        action = None
        for rule in RULES["global"]:
            base.LOGGER.debug("Checking rule: ", rule)
            if rule.check(cmsg):
                base.LOGGER.debug("Running module")
                if rule.module.is_async:
                    action = await rule.module.async_run(cmsg)
                else:
                    action = rule.module.run(cmsg)
                if rule.exclusive:
                    base.LOGGER.debug("Exclusive rule, breaking execution")
                    break

        if action is None:
            break
        if action.message:
            await cmsg.respond(action.message)
        if action.reaction:
            await cmsg.react(action.reaction)

    # Legacy beep boop detection, to be refactored
    if len(cmsg.words) == 1:
        if "beep" in cmsg.words:
            await message.channel.send("boop")
            return
        if "boop" in cmsg.words:
            await message.channel.send("beep")
            return

    # Log debug string
    base.LOGGER.debug(cmsg.dbgstring())

    # Admin commands
    if au == "Meky#8888":
        await admin_commands(cmsg)

    # Cookie reaction
    if rn == 1 and message.author != BOT.user:
        await message.add_reaction(base.EMOJI_COOKIE)


async def admin_commands(cmsg):
    if "!dbg" in cmsg.raw:
        await cmsg.respond(cmsg.dbgstring())
    elif "!reloadcli" in cmsg.raw:
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


RULES = {
    "global": [
        # main, exclusive rules
        base.Rule("!help", base.Rule.STARTS_WITH, base.StrFuncCall(get_help_message)),
        base.Rule("!introspect", base.Rule.STARTS_WITH, base.StrFuncCall(get_introspection_result)),
        base.Rule("!cat", base.Rule.STARTS_WITH, base.Module("Catbot CLI", base.Module.NATIVE, handler=CLI.handle)),
        base.Rule("!define ", base.Rule.STARTS_WITH, base.FuncCall(macro.define)),
        base.Rule("!undefine ", base.Rule.STARTS_WITH, base.FuncCall(macro.undefine)),
        base.Rule("!macros", base.Rule.STARTS_WITH, base.StrFuncCall(macro.listmacros)),
        base.Rule("/", base.Rule.STARTS_WITH, base.AsyncFuncCall(process_macro)),
        base.Rule("!a ", base.Rule.STARTS_WITH, base.AsyncFuncCall(ai_process)),
        base.Rule("!roll ", base.Rule.STARTS_WITH, base.StrFuncCall(dice_roll)),

        # reaction rules
        base.RuleOp.rules_and().rules(
            base.AsyncFuncCall(wise_response),
            base.Rule("mentioned", base.Rule.FLAGS_ALL, None),
            base.Rule(["question", "inquiry" "indirect_inquiry"], base.Rule.FLAGS_ONE_OF, None)
        ),
        base.Rule(["morning", "myrming"], base.Rule.FLAGS_ONE_OF, base.SimpleReaction(base.EMOJI_SUN)),
        base.Rule("night", base.Rule.FLAGS_ALL, base.SimpleReaction(base.EMOJI_MOON)),
        base.Rule(["greeting", "farewell"], base.Rule.FLAGS_ONE_OF, base.SimpleReaction(base.EMOJI_WAVE))
    ]
}

BOT.run(load_token())
