import requests
import catbot.botbase as base


class DogApi(base.AsyncModule):
    def __init__(self):
        super().__init__("DogAPI", base.Module.NATIVE, handler=self.handle)

    async def handle(self, cmsg):
        try:
            resp = requests.get("https://dog.ceo/api/breeds/image/random")
            img_url = resp.json()["message"]
            if "http" not in img_url:
                raise Exception("Invalid URL")
            await cmsg.respond(img_url)
        except Exception as ex:
            base.LOGGER.error(ex)
            await cmsg.respond("Failed to get doggo picture " + base.EMOJI_BLOBCATNOTLIKE)

