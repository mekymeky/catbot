import time
import http3

from discord import Embed
import catbot.botbase as base


class CatbotConvMemory(base.AsyncModule):
    memories = []

    @staticmethod
    def get_memories():
        return CatbotConvMemory.memories

    @staticmethod
    def get_memories_str():
        text = "\n".join(CatbotConvMemory.memories)
        if len(text) > 1700:
            text = text[:1700] + "\n..."
        return text

    def __init__(self):
        super().__init__("CatbotConvMemoriesModule", base.Module.NATIVE, handler=self.show_memories)

    async def show_memories(self, cmsg):
        max_memories = 30

        e = Embed(title="Catbot Memory", color=base.COLOR_MAIN)
        e.set_thumbnail(url=str(cmsg.bot.user.avatar.url))
        memory_count = len(CatbotConvMemory.memories)

        e.add_field(name="Current memories", value=f"{memory_count}")
        if memory_count == 0:
            e.add_field(name="_ _", value="enmpty", inline=False)
        else:
            for memory in CatbotConvMemory.memories[:max_memories]:
                e.add_field(name="_ _",
                            value=str(memory),
                            inline=False)
            if memory_count > max_memories:
                e.add_field(name="_ _",
                            value="...",
                            inline=False)
        e.set_footer(text=cmsg.bot_name + " version " + cmsg.version)
        await cmsg.embed(e)


class CatbotConversation(base.AsyncModule):

    def __init__(self, enabled=True):
        super().__init__("CatbotConversationModule", base.Module.NATIVE, handler=self.process)
        self.enabled = enabled
        self.version = "0.0.1"
        self.base_url = "http://127.0.0.1:8881"
        self._busy = False
        self._http_client = http3.AsyncClient()

    def _postprocess(self, text):
        res = ""
        cap_next = True
        for letter in text:
            if (cap_next and (not letter in [" ", ","])):
                res += letter.upper()
                cap_next = False
            else:
                res += letter
            if (letter in [".", "!", "?"]):
                cap_next = True

        res = res.replace(" i ", " I ")
        res = res.replace(" i'", " I'")
        res = res.replace("_POTENTIALLY_UNSAFE__", "")
        res = res.replace("Your persona: ", "(me) ")
        res = res.replace("Partner's persona: ", "(partner) ")


        return res.strip()

    async def process(self, cmsg):
        if not self.enabled:
            await cmsg.respond("Experimental conversation module is disabled.")
            return base.NO_MESSAGE_ACTION

        command_start = cmsg.raw_lower[5:20]
        if command_start.startswith("meminject "):
            text = "your persona: " + cmsg.raw[15:].strip()
            memory_injection = True
        else:
            text = cmsg.raw[7:].strip()
            memory_injection = False

        if self._busy:
            await cmsg.react(base.EMOJI_BLOBCATCONFUSE)
            return

        response = None
        try:
            self._busy = True
            async with cmsg.discord_msg.channel.typing():
                response = await self.request(text)
        finally:
            self._busy = False

        if response == "#ERROR":
            await cmsg.respond(f"AI module error {base.EMOJI_BLOBCATGOOGLYGUN}")
        elif response == "#FAILED":
            await cmsg.respond(f"AI request failed {base.EMOJI_BLOBCATNOTLIKE}")
        else:
            if memory_injection:
                await cmsg.respond("Done.")
            else:
                await cmsg.respond(response)

        return base.NO_MESSAGE_ACTION

    async def test(self):
        try:
            print("AIM TEST")
            response_data = await self._http_client.post(f"{self.base_url}/", data="#TEST", timeout=3)
            response = response_data.text
            print("AIM RES: " + str(response))
            return response == "#OK"
            
        except Exception as ex:
            print(ex)
            return False

    async def request(self, text):
        req_start = time.time()
        try:
            response_data = await self._http_client.post(f"{self.base_url}/interact", data=text, timeout=250)
            response_json = response_data.json()
            response = self._postprocess(response_json["text"])
            CatbotConvMemory.memories = list(map(self._postprocess, response_json["memories"]))
            print("RES JSON: " + str(response_json))
            print("AIM RES: " + str(response))
            return response
            
        except Exception as ex:
            print(ex)
            return "#FAILED"
        finally:
            req_end = time.time()
            print(f"AI req took {req_end - req_start}s")
