import pickle
import threading

MACRO_RELOAD = True
MACRO_TABLE = {}
MACRO_LOCK = threading.Semaphore()
FILE_LOCK = threading.Semaphore()


def reload():
    global MACRO_RELOAD
    global MACRO_TABLE
    global FILE_LOCK

    if not MACRO_RELOAD:
        return

    FILE_LOCK.acquire()
    try:
        f = open("../macros.p", "rb")
        MACRO_TABLE = pickle.load(f)
        f.close()
    except Exception as ex:
        print(ex)
    FILE_LOCK.release()

    MACRO_RELOAD = False


def write():
    global MACRO_RELOAD
    global MACRO_TABLE
    global FILE_LOCK
    FILE_LOCK.acquire()
    try:
        f = open("../macros.p", "wb")
        pickle.dump(MACRO_TABLE, f)
        f.close()
        MACRO_RELOAD = True
    except Exception as ex:
        print(ex)
    FILE_LOCK.release()


def run(cmsg, macro_variable):
    global MACRO_TABLE
    reload()
    if not macro_variable:
        return ""

    if macro_variable[0] == "/":
        macroname = macro_variable[1::]
    else:
        macroname = macro_variable
    try:
        return MACRO_TABLE[cmsg.server_id][macroname]
    except Exception as ex:
        print(ex)
        return ""


def define(cmsg):
    global MACRO_TABLE
    global MACRO_LOCK
    tmp = cmsg.raw.split(" ")
    MACRO_LOCK.acquire()
    try:
        tmp.pop(0)
        macroname = tmp.pop(0)
        macrotext = " ".join(tmp)
        if not (cmsg.server_id in MACRO_TABLE):
            MACRO_TABLE[cmsg.server_id] = {}
        MACRO_TABLE[cmsg.server_id][macroname] = macrotext
        write()
    except Exception as ex:
        print(ex)
    MACRO_LOCK.release()


def undefine(cmsg):
    global MACRO_TABLE
    global MACRO_LOCK
    MACRO_LOCK.acquire()
    try:
        macronames = cmsg.raw[10::].split(" ")
        for macroname in macronames:
            if cmsg.server_id in MACRO_TABLE:
                del(MACRO_TABLE[cmsg.server_id][macroname])
        write()
    except Exception as ex:
        print(ex)
    MACRO_LOCK.release()


def listmacros(cmsg):
    global MACRO_TABLE
    global MACRO_LOCK
    reload()
    MACRO_LOCK.acquire()
    try:
        names = MACRO_TABLE[cmsg.server_id].keys()
        MACRO_LOCK.release()
        if len(names) == 0:
            return "No macros defined."
        return ", ".join(names)
    except Exception as ex:
        MACRO_LOCK.release()
        print(ex)
        return "No macros defined."
