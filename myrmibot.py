#!python3
# -*- coding: utf-8 -*-
import discord, asyncio
import pickle
import random
import datetime
import macromodule as macro
import catbotcli
import dice
import importlib
import aimodule

description = "The best bot, the catbot."


CURR = 0

bot = discord.Client()

CLI = catbotcli.CatCLI()

AIM = aimodule.AIModule()

LASTDAY = None

UNCERTAIN_QUESTIONS_ENABLED = True

def __RELOAD_CLI__():
    global CLI
    importlib.reload(catbotcli)
    CLI = catbotcli.CatCLI()

def roll(a, b=None):
    if b is None:
        b = a
        a = 1
    return random.randint(a,b)

def specialMsgDeserved():
    global LASTDAY
    today = datetime.datetime.now().day
    if LASTDAY is None:
        if roll(100)==1:
            LASTDAY = today
            return True
    elif LASTDAY != today:
        LASTDAY = None #week-long fail safety
        if roll(100)==1:
            LASTDAY = today
            return True


class MyrmibotMessage():
    def __init__(self, msg):
        self.raw = self.cleanSpace(msg.content.lower()).strip()
        self.msg = self.cleanMsg(msg.content)
        self.words = self.msg.split()

        self.botName = bot.user.name
        self.mentioned = False
        self.initMention()
        
        self.isQuestion = False
        self.isExclamation = False
        self.isGreeting = False
        self.isFarewell = False
        self.isNight = False
        self.isMorning = False
        self.isMyrming = False
        self.isInquiry = False
        self.isIndirectInquiry = False
        
        self.assessType()

    def containsWords(self, wlist):
        if wlist is None:
            return False
        if len(wlist)==0:
            return False
        
        for w in wlist:
            if not (w in self.raw):
                return False
        return True

    def initMention(self):
        if self.botName.lower() in self.raw or "<@439045787041660928>" in self.raw or "<@!439045787041660928>" in self.raw:
            self.mentioned = True

    def assessType(self):

        if self.containsWords(["what", "do", "you", "think"]) or self.containsWords(["what", "do", "you", "say"]) or self.containsWords(["what", "say", "you"]):
            self.isInquiry = True

        if self.containsWords(["what", "does", "say"]) or self.containsWords(["what", "does", "think"]) or self.containsWords(["what", "does", "say"]) or self.containsWords(["what's", "thinking"]) or self.containsWords(["what's", "opinion"]) or self.containsWords(["do", "you", "think"]):
            self.isIndirectInquiry = True

        if UNCERTAIN_QUESTIONS_ENABLED and self.mentioned:
            if "?" in self.raw:
                print ("uncertain question")
                self.isInquiry = True
                self.isQuestion = True

        if ((self.raw.startswith("<@439045787041660928>") or self.raw.startswith(" <@439045787041660928>")) and (self.raw.endswith("?") or self.raw.endswith("? "))) or self.raw.endswith("?<@439045787041660928>") or self.raw.endswith("? <@439045787041660928>") or self.raw.endswith("?  <@439045787041660928>") or self.raw.endswith("<@439045787041660928> ?") or self.raw.endswith("<@439045787041660928>?"):
            print ("vague question")
            self.isInquiry = True

            
        if len(self.msg)>3:
            suffix = self.raw[-4::]
            if "?" in suffix:
                self.isQuestion = True
            if "!" in suffix:
                self.isExclamation = True


        if len(self.words)<6:
            if self.containsWords(["that", "right"]) and self.isQuestion:
                self.isInquiry = True
            if "hello" in self.words or "hi" in self.words or "greetings" in self.words or "henlo" in self.words or "hii" in self.words or "sup" in self.words or "soup" in self.words or "what's up"  in self.msg:
                self.isGreeting = True
            if "cya" in self.words or "see you" in self.msg or "bye" in self.words or "good night" in self.msg or "night night" in self.msg or "nn" in self.words or "nini" in self.words or " o/" in self.msg or "\\o " in self.msg:
                self.isFarewell = True
            if "nighty night" in self.msg or "sleep well" in self.msg or "nini" in self.words or "sweet dreams" in self.msg or "night night"  in self.msg or "good night" in self.msg or "nn" in self.words:
                self.isNight = True
            if "myrming" in self.words:
                self.isMyrming = True
            if "morning" in self.words:
                self.isMorning = True

            if len(self.words) in [1,2]:
                if "hey" in self.words:
                    self.isGreeting = True
                if "night" in self.words:
                    self.isNight = True

    def cleanMsg(self, msg):
        msg = msg.lower()
        msg = msg.replace(".", "")
        msg = msg.replace(",", "")
        msg = msg.replace("!", "")
        msg = msg.replace("?", "")
        msg = msg.replace("\n", " ")
        msg = msg.replace("\t", " ")
        msg = self.cleanSpace(msg)
        return msg

    def cleanSpace(self, msg):
        msg = msg.replace("\n", " ")
        msg = msg.replace("\t", " ")
        msg = msg.replace("  ", " ")
        msg = msg.replace("  ", " ")
        msg = msg.replace("  ", " ")
        if " " in msg[-1::]: msg = msg[:-1]
        if " " in msg[-1::]: msg = msg[:-1]
        return msg

    def dbgstring(self):
        res = "ml:"+str(len(self.msg)) + " wc:"+str(len(self.words)) + " flags: " + str([self.isQuestion, self.isExclamation, self.isGreeting, self.isFarewell, self.isNight, self.isMorning, self.isMyrming, self.isInquiry, self.isIndirectInquiry])
        return res
    

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


def guess():
    r = random.randint(0,9)

    if r==0:
        return "Definitely."
    elif r<=2:
        return "Yes."
    elif r<=4:
        return "No."
    elif r<=5:
        return "Nope."
    elif r<=7:
        return "Perhaps."
    elif r<=8:
        return "Maybe."
    elif r==9:
        return "mlem"
        
def get_help_message():
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

def get_introspection_result():
    aim_accessible = AIM.test()
    result = "```"
    result += "AIM accessible: " + str(aim_accessible) + "\n"
    result += "```"
    return result

@bot.event
async def on_message(message):
    content = str(message.content)
    mc = str(message.content).lower()
    au = str(message.author)
    cn = str(message.channel)
    mm = MyrmibotMessage(message)
    rn = roll(1000)
    print("rn:", rn)
    print(mm.raw)

    if (message.author == bot.user): return;

    if (mm.raw.startswith("!help")):
        await message.channel.send(get_help_message())
        return

    if (mm.raw.startswith("!a ")):
        response = AIM.process(mm.raw[3::])
        await message.channel.send(response)
        return

    if (mm.raw.startswith("!introspect")):
        await message.channel.send(get_introspection_result())
        return

    if (mm.raw.startswith("!cat")):
        response = CLI.handle(content)
        if (not response is None) and (response != ""):
            await message.channel.send(response)
    
    if (mm.raw.startswith("!roll ")):
        rollmsg = str(dice.roll(content[6::]))
        if "[" in rollmsg and "]" in rollmsg:
            rollmsg = rollmsg[1:-1]
        await message.channel.send(rollmsg)
        return 
    elif (mm.raw.startswith("!define ")):
        macro.define(message, content)
        return
    elif (mm.raw.startswith("!undefine ")):
        macro.undefine(message, content)
        return
    elif (mm.raw.startswith("!macros")):
        await message.channel.send(macro.listmacros(message))
        return
    elif (mm.raw.startswith("/")):
        chain = mm.raw.split(" ")
        emptychain = True
        for mtext in chain:
            resp = macro.run(message, mtext)
            if not (resp == ""):
                emptychain = False
                await message.channel.send(resp)
        if not emptychain:
            await message.delete()
        return

    if (len(mm.words) == 1):
        if "beep" in mm.words:
            await message.channel.send("boop")
            return
        if "boop" in mm.words:
            await message.channel.send("beep")
            return

    print(mm.dbgstring())
    if au == "Meky#8888":
        if "!dbg" in mm.raw:
            await message.channel.send(mm.dbgstring())
        elif "!reloadcli" in mm.raw:
            try:
                __RELOAD_CLI__()
                resp = CLI.reloadMessage()
            except Exception as err:
                resp = "`" + str(err) + "`"
            await message.channel.send(resp)


    #if cn=="art":
    #    if message.attachments or "cdn.discordapp.com/attachments" in mm.raw:
    #        await message.add_reaction("❤")
    
    if rn == 1 and message.author != bot.user:
            await message.add_reaction("🍪")

      

    if mm.isMyrming:
        await message.add_reaction("🌞")
        
    elif mm.mentioned:
        if mm.isInquiry and mm.isQuestion:
            await message.add_reaction("🤔")
            await asyncio.sleep(1)
            await message.channel.send(guess())
        elif mm.isGreeting:
            await message.add_reaction("👋")
        elif mm.isMorning or mm.isMyrming:
            await message.add_reaction("🌞")
        elif mm.isNight:
            await message.add_reaction("🌘")
        elif mm.isFarewell:
            await message.add_reaction("👋")

    elif bot.user in message.mentions:
        if mm.isInquiry or mm.isIndirectInquiry: # no need for question mark in direct mention
            await message.add_reaction("🤔")
            await asyncio.sleep(1)
            await message.channel.send(guess())
        elif mm.isGreeting:
            await message.add_reaction("👋")
        elif mm.isMorning or mm.isMyrming:
            await message.add_reaction("🌞")
        elif mm.isNight:
            await message.add_reaction("🌘")
        elif mm.isFarewell:
            await message.add_reaction("👋")
    
    else:
        if mm.isGreeting:
            await message.add_reaction("👋")
        elif mm.isMorning or mm.isMyrming:
            await message.add_reaction("🌞")
        elif mm.isNight:
            await message.add_reaction("🌘")
        elif mm.isFarewell:
            await message.add_reaction("👋")


        

        
            



bot.run('REPLACEME')
