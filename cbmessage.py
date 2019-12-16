import asyncio
import discord

UNCERTAIN_QUESTIONS_ENABLED = True


class CatbotMessage:
    def __init__(self, bot, discord_msg):
        self.raw = self.trim_spaces(discord_msg.content.lower()).strip()
        self.msg = self.clean_msg(discord_msg.content)
        self.discord_msg = discord_msg
        self.words = self.msg.split()
        self.server_id = discord_msg.guild.id
        self.bot = bot
        self.bot_name = bot.user.name
        self.author = str(discord_msg.author)
        self.channel = str(discord_msg.channel)

        self.flags = {
            "mentioned": False,
            "name_mentioned": False,
            "question": False,
            "exclamation": False,
            "greeting": False,
            "farewell": False,
            "night": False,
            "morning": False,
            "myrming": False,
            "inquiry": False,
            "indirect_inquiry": False
        }

        self.init_mentions()

        self.assess_type()

    async def respond(self, response):
        await self.discord_msg.channel.send(response)

    async def react(self, reaction):
        await self.discord_msg.add_reaction(reaction)

    async def sleep(self, seconds):
        await asyncio.sleep(seconds)

    # TODO not yet working properly
    async def send_image(self, url):
        embed = discord.Embed()
        embed.set_image(url=url)
        await self.discord_msg.channel.send(embed=embed)

    async def delete(self):
        await self.discord_msg.delete()

    def contains_words(self, wlist):
        if wlist is None:
            return False
        if len(wlist) == 0:
            return False

        for w in wlist:
            if not (w in self.raw):
                return False
        return True

    def init_mentions(self):
        if self.bot_name.lower() in self.raw or "<@439045787041660928>" in self.raw or "<@!439045787041660928>" in self.raw:
            self.flags["mentioned"] = True
        if self.bot_name in self.words:
            self.flags["name_mentioned"] = True

    def assess_type(self):

        if self.contains_words(["what", "do", "you", "think"]) or self.contains_words(
                ["what", "do", "you", "say"]) or self.contains_words(["what", "say", "you"]):
            self.flags["inquiry"] = True

        if self.contains_words(["what", "does", "say"]) or self.contains_words(
                ["what", "does", "think"]) or self.contains_words(["what", "does", "say"]) or self.contains_words(
                ["what's", "thinking"]) or self.contains_words(["what's", "opinion"]) or self.contains_words(
                ["do", "you", "think"]):
            self.flags["indirect_inquiry"] = True

        if UNCERTAIN_QUESTIONS_ENABLED and self.flags["mentioned"]:
            if "?" in self.raw:
                print("uncertain question")
                self.flags["inquiry"] = True
                self.flags["question"] = True

        if ((self.raw.startswith("<@439045787041660928>") or self.raw.startswith(" <@439045787041660928>")) and (
                self.raw.endswith("?") or self.raw.endswith("? "))) or self.raw.endswith(
                "?<@439045787041660928>") or self.raw.endswith("? <@439045787041660928>") or self.raw.endswith(
                "?  <@439045787041660928>") or self.raw.endswith("<@439045787041660928> ?") or self.raw.endswith(
                "<@439045787041660928>?"):
            print("vague question")
            self.flags["inquiry"] = True

        if len(self.msg) > 3:
            suffix = self.raw[-4::]
            if "?" in suffix:
                self.flags["question"] = True
            if "!" in suffix:
                self.flags["exclamation"] = True

        if len(self.words) < 6:
            if self.contains_words(["that", "right"]) and self.flags["question"]:
                self.flags["inquiry"] = True
            if "hello" in self.words or "hi" in self.words or "greetings" in self.words or "henlo" in self.words or "hii" in self.words or "sup" in self.words or "soup" in self.words or "what's up" in self.msg:
                self.flags["greeting"] = True
            if "cya" in self.words or "see you" in self.msg or "bye" in self.words or "good night" in self.msg or "night night" in self.msg or "nn" in self.words or "nini" in self.words or " o/" in self.msg or "\\o " in self.msg:
                self.flags["farewell"] = True
            if "nighty night" in self.msg or "sleep well" in self.msg or "nini" in self.words or "sweet dreams" in self.msg or "night night" in self.msg or "good night" in self.msg or "nn" in self.words:
                self.flags["night"] = True
            if "myrming" in self.words:
                self.flags["myrming"] = True
            if "morning" in self.words:
                self.flags["morning"] = True

            if len(self.words) in [1, 2]:
                if "hey" in self.words:
                    self.flags["greeting"] = True
                if "night" in self.words:
                    self.flags["night"] = True

    def clean_msg(self, msg):
        msg = msg.lower()
        msg = msg.replace(".", "")
        msg = msg.replace(",", "")
        msg = msg.replace("!", "")
        msg = msg.replace("?", "")
        msg = msg.replace("\n", " ")
        msg = msg.replace("\t", " ")
        msg = self.trim_spaces(msg)
        return msg

    def trim_spaces(self, msg):
        msg = msg.replace("\n", " ")
        msg = msg.replace("\t", " ")
        msg = msg.replace("  ", " ")
        msg = msg.replace("  ", " ")
        msg = msg.replace("  ", " ")
        if " " in msg[-1::]:
            msg = msg[:-1]
        if " " in msg[-1::]:
            msg = msg[:-1]
        return msg

    def dbgstring(self):
        res = "ml:" + str(len(self.msg)) + " wc:" + str(len(self.words)) + " flags: " + str(self.flags)
        return res
