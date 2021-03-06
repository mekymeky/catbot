import requests
import catbot.botbase as base


class CatApi(base.AsyncModule):
    def __init__(self):
        super().__init__("CatAPI", base.Module.NATIVE, handler=self.handle)

    async def handle(self, cmsg):
        try:
            resp = requests.get("https://api.thecatapi.com/v1/images/search",
                                headers={"x-api-key": "3777718a-f4ab-41c8-b3c1-be2e834ff28c"})
            img_url = resp.json()[0]["url"]
            await cmsg.respond(img_url)
        except Exception as ex:
            base.LOGGER.error(ex)
            await cmsg.respond("Failed to get kitty picture " + base.EMOJI_BLOBCATNOTLIKE)

