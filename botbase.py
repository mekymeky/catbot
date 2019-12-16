# -*- coding: utf-8 -*-

from cbmessage import CatbotMessage

BOT_UID = "<@439045787041660928>"

EMOJI_THINK = "🤔"
EMOJI_COOKIE = "🍪"
EMOJI_HEART = "❤"
EMOJI_WAVE = "👋"
EMOJI_SUN = "🌞"
EMOJI_MOON = "🌘"
EMOJI_BLOBCATNOTLIKE = "<:blobcatnotlike:618892026930397214>"
EMOJI_BLOBCATGOOGLYGUN = "<:blobcatgooglygun:618892026687127552>"
EMOJI_ANGELBLOBCAT = "<:angelblobcat:618892026284343316>"


class LogLevel:
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3


class Logger:
    def __init__(self, level=LogLevel.DEBUG, method=None):
        if method is None:
            self.method = self.print_log
        else:
            self.method = method
        self.level = level

    def debug(self, *args):
        if self.level >= LogLevel.DEBUG:
            self.method(*tuple(["DEBUG:"]) + args)

    def info(self, *args):
        if self.level >= LogLevel.INFO:
            self.method(*tuple(["INFO:"]) + args)

    def warn(self, *args):
        if self.level >= LogLevel.WARN:
            self.method(*tuple(["WARN:"]) + args)

    def error(self, *args):
        if self.level >= LogLevel.ERROR:
            self.method(*tuple(["ERROR:"]) + args)

    def print_log(self, *args):
        print(*args)


LOGGER = Logger()


class Action:
    CONTINUE = 0
    END = 1
    ERROR = 2

    def __init__(self, action_type, message=None, reaction=None):
        self.type = action_type
        self.message = message
        self.reaction = reaction

    def __str__(self):
        typestr = ""
        if self.type == Action.CONTINUE:
            typestr = "CONTINUE"
        elif self.type == Action.END:
            typestr = "END"
        elif self.type == Action.ERROR:
            typestr = "ERROR"

        if self.message is None:
            msgstr = "None"
        else:
            msgstr = "\"" + self.message + "\""

        return typestr.ljust(8) + " msg=" + msgstr + " reaction=" + str(self.reaction)


NO_MESSAGE_ACTION = Action(Action.END)


class RestModule:
    def __init__(self, url):
        self.url = url

    # TODO
    def run(self, *args):
        pass


class Module:
    NATIVE = 0
    REST_API = 1

    def __init__(self, name, module_type, handler=None, url=None, is_async=False):
        self.name = name
        self.type = module_type
        self.handler = handler
        self.url = url
        self.is_async = is_async
        self.validate()
        if self.type == Module.REST_API:
            self.handler = RestModule(url).run

    def validate(self):
        if self.type == Module.NATIVE:
            assert self.handler is not None
        elif self.type == Module.REST_API:
            assert self.url is not None

    async def run(self, cmsg):
        if self.is_async:
            return await self.handler(cmsg)
        else:
            return await cmsg.bot.loop.run_in_executor(None, self.handler, cmsg)

    def __str__(self):
        result = "\n\t\tModule(" + TYPENAMES[Module][self.type]
        result += ": name=" + self.name
        result += ", handler=" + str(self.handler)
        result += ", url=" + str(self.url)
        result += ", is_async=" + str(self.is_async)
        result += ")"
        return result


class AsyncModule(Module):
    def __init__(self, name, module_type, handler=None, url=None):
        super().__init__(name, module_type, handler, url, True)


class FuncCall(Module):
    def __init__(self, function):
        super().__init__("Function call", Module.NATIVE, handler=function)


class AsyncFuncCall(AsyncModule):
    def __init__(self, function):
        super().__init__("Async function call", Module.NATIVE, handler=function)


class StrFuncCall(Module):
    def __init__(self, function):
        super().__init__("String function call", Module.NATIVE, handler=function)

    # overrides Module.run
    async def run(self, cmsg):
        return Action(Action.END, await super().run(cmsg))


class SimpleMessage(Module):
    def __init__(self, message):
        self.message = message
        super().__init__("Response: " + str(message), Module.NATIVE)

    def validate(self):
        assert self.message

    def run(self, cmsg):
        return Action(Action.END, message=self.message)


class SimpleReaction(Module):
    def __init__(self, reaction):
        self.reaction = reaction
        super().__init__("Reaction: " + str(reaction), Module.NATIVE)

    def validate(self):
        assert self.reaction

    def run(self, cmsg):
        return Action(Action.END, reaction=self.reaction)


class Rule:
    MATCH = 0  # exactly matches conditions (depending on case sensitivity)
    CONTAINS_ALL = 1  # contains all conditions
    CONTAINS_ONE_OF = 2  # contains at least one of conditions
    STARTS_WITH = 3  # starts with at least one of conditions
    COMMAND = 4
    FLAGS_ALL = 5
    FLAGS_ONE_OF = 6
    CUSTOM = 7

    def __init__(self, conditions, rule_type, module, exclusive=True, custom_method=None, process_raw=True):
        self.conditions = conditions
        self.type = rule_type
        self.module = module
        self.exclusive = exclusive
        self.custom_method = custom_method
        self.process_raw = process_raw

    def check(self, cmsg):
        method = None
        if self.type in [Rule.CONTAINS_ALL, Rule.CONTAINS_ONE_OF]:
            method = self.check_contains
        elif self.type == Rule.MATCH:
            method = self.check_match
        elif self.type in [Rule.STARTS_WITH, Rule.COMMAND]:
            method = self.check_starts_with
        elif self.type in [Rule.FLAGS_ALL, Rule.FLAGS_ONE_OF]:
            method = self.check_flag
        elif self.type == Rule.CUSTOM:
            method = self.custom_method
        else:
            LOGGER.error("Unknown rule type:", self.type)
            return False

        match_all = self.type in [Rule.CONTAINS_ALL, Rule.FLAGS_ALL]

        if isinstance(self.conditions, list):
            for cond in self.conditions:
                if match_all:
                    if not method(cond, cmsg):
                        return False
                else:
                    if method(cond, cmsg):
                        return True
            return match_all
        elif isinstance(self.conditions, str):
            return method(self.conditions, cmsg)
        else:
            LOGGER.error("Unsupported condition type:", type(self.conditions))
            return False

    def get_content_str(self, content):
        if isinstance(content, str):
            return content
        elif isinstance(content, CatbotMessage):
            if self.process_raw:
                return content.raw
            else:
                return content.msg
        else:
            LOGGER.error("Unsupported content type:", type(content))
            return ""

    def check_contains(self, condition, cmsg):
        content_str = self.get_content_str(cmsg)
        return condition in content_str

    def check_match(self, condition, cmsg):
        content_str = self.get_content_str(cmsg)
        return content_str == condition

    def check_starts_with(self, condition, cmsg):
        content_str = self.get_content_str(cmsg)
        return content_str.startswith(condition)

    def check_flag(self, flag, cmsg):
        return cmsg.flags[flag]

    def __str__(self):
        result = "\n\tRule(" + TYPENAMES[Rule][self.type]
        result += ": conditions=" + str(self.conditions)
        result += ", exclusive=" + str(self.exclusive)
        result += ", custom_method=" + str(self.custom_method)
        result += ", process_raw=" + str(self.process_raw)
        result += ", module=" + str(self.module)
        result += "\n\t)"
        return result


class RuleOp(Rule):
    OP_TYPE_OR = 0
    OP_TYPE_AND = 1

    def __init__(self, operator_type, exclusive):
        super().__init__(None, None, None, exclusive=exclusive)
        self.type = operator_type
        self.rules_list = []

    def rules(self, module, *rules):
        self.module = module
        if rules is None:
            self.rules_list = []
        else:
            self.rules_list = rules
        return self

    def check(self, cmsg):
        match_all = self.type == RuleOp.OP_TYPE_AND
        for rule in self.rules_list:
            if match_all:
                if not rule.check(cmsg):
                    return False
            else:
                if rule.check(cmsg):
                    return True
        return match_all

    def __str__(self):
        result = "RuleOp(" + TYPENAMES[RuleOp][self.type]
        result += ": exclusive=" + str(self.exclusive)
        result += ", rules=" + str(self.rules_list)
        result += ")"
        return result

    @staticmethod
    def rules_or(exclusive=True):
        return RuleOp(RuleOp.OP_TYPE_OR, exclusive=exclusive)

    @staticmethod
    def rules_and(exclusive=True):
        return RuleOp(RuleOp.OP_TYPE_AND, exclusive=exclusive)


TYPENAMES = {
    RuleOp: {
        RuleOp.OP_TYPE_OR: "OR",
        RuleOp.OP_TYPE_AND: "AND"
    },
    Rule: {
        Rule.MATCH: "MATCH",
        Rule.CONTAINS_ONE_OF: "CONTAINS_ONE_OF",
        Rule.STARTS_WITH: "STARTS_WITH",
        Rule.COMMAND: "COMMAND",
        Rule.FLAGS_ALL: "FLAGS_ALL",
        Rule.FLAGS_ONE_OF: "FLAGS_ONE_OF",
        Rule.CUSTOM: "CUSTOM"
    },
    Module: {
        Module.NATIVE: "NATIVE",
        Module.REST_API: "REST_API"
    },
    Action: {
        Action.CONTINUE: "CONTINUE",
        Action.END: "END",
        Action.ERROR: "ERROR"
    }
}
