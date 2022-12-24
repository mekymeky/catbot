import catbot.botbase as base
from discord import Embed


class MeowMeowProtocol(base.AsyncModule):
    def __init__(self):
        super().__init__("MeowMeowProtocol", base.Module.NATIVE, handler=self.handle)

    async def handle(self, cmsg):
        if cmsg.raw.startswith(base.EMOJI_CAT + " meow"):
            cmsg.config["mmp_channel"] = cmsg.channel
            cmsg.commit_config()

            e = Embed(title="Meow Meow Protocol", color=base.COLOR_GREEN)
            e.set_thumbnail(url=str(cmsg.bot.user.avatar.url))
            e.add_field(name="Success", value="Channel registered", inline=False)
            e.set_footer(text=cmsg.bot_name + " version " + cmsg.version)
            await cmsg.embed(e)
        # TODO
