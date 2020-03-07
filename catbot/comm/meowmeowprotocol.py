import catbot.botbase as base
from discord import Embed


class MeowMeowProtocol(base.AsyncModule):
    def __init__(self):
        super().__init__("MeowMeowProtocol", base.Module.NATIVE, handler=self.handle)

    async def handle(self, cmsg):
        if cmsg.raw.startswith(base.EMOJI_CAT + " meow"):
            e = Embed(title="Meow Meow Protocol Exception", color=0xff6459)
            e.set_thumbnail(url=str(cmsg.bot.user.avatar_url))
            cp = cmsg.command_prefix
            e.add_field(name="RuntimeError", value="Not yet implemented", inline=False)
            e.set_footer(text=cmsg.bot_name + " version " + cmsg.version)
            await cmsg.embed(e)
        # TODO
