from catbot.serverconfig import CatbotConfig


def run(cmsg, macro_variable):
    macro_table = cmsg.config.get("macros", {})
    if not macro_variable:
        return ""

    if macro_variable[0] == "/":
        macroname = macro_variable[1::]
    else:
        macroname = macro_variable
    return macro_table.get(macroname, "")


def define(cmsg):
    macro_table = cmsg.config.get("macros", {})
    tmp = cmsg.raw.split(" ")
    try:
        tmp.pop(0)
        macroname = tmp.pop(0)
        macrotext = " ".join(tmp)
        macro_table[macroname] = macrotext
        cmsg.config["macros"] = macro_table
        CatbotConfig.commit_config(cmsg.server_id, cmsg.config)
    except Exception as ex:
        print(ex)


def undefine(cmsg):
    macro_table = cmsg.config.get("macros", {})
    try:
        macronames = cmsg.raw[10::].split(" ")
        for macroname in macronames:
            if macroname in macro_table:
                del(macro_table[macroname])
        CatbotConfig.commit_config(cmsg.server_id, cmsg.config)
    except Exception as ex:
        print(ex)


def listmacros(cmsg):
    macro_table = cmsg.config.get("macros", {})
    try:
        names = macro_table.keys()
        if len(names) == 0:
            return "No macros defined."
        return ", ".join(names)
    except Exception as ex:
        print(ex)
        return "No macros defined."
