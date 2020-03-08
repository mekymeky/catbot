import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from keras.models import load_model
from keras_efficientnets import EfficientNetB5
import time
from discord import Embed
from datetime import datetime
import catbot.botbase as base
from PIL import Image, ImageOps
import numpy as np
import io


def url_has_image(url):
    url = url.lower()
    return ".png" in url or ".jpg" in url or ".gif" in url


class HasImageRule(base.Rule):
    def __init__(self, module):
        super().__init__(None, base.Rule.CUSTOM, module)

    def check(self, cmsg):
        attachments = cmsg.discord_msg.attachments
        if attachments is None:
            return False
        for attachment in attachments:
            if url_has_image(attachment.url):
                return True
        return False


class CatbotVisionHistory(base.AsyncModule):
    def __init__(self):
        super().__init__("CatbotVisionModule", base.Module.NATIVE, handler=self.show_history)

    async def show_history(self, cmsg):
        history = CatbotVision.history.get(cmsg.server_id, [])

        e = Embed(title="Catbot Vision History", color=0x27e69d)
        e.set_thumbnail(url=str(cmsg.bot.user.avatar_url))
        if len(history) == 0:
            e.add_field(name="_ _", value="No records available", inline=False)
        else:
            for record in history:
                e.add_field(name=str(datetime.fromtimestamp(record[0])),
                            value="Cat: {}%\nProcessing time: {}s".format(round(record[2]*100, 2),
                                                                          round(record[1], 2)),
                            inline=False)
        e.set_footer(text=cmsg.bot_name + " version " + cmsg.version)
        await cmsg.embed(e)


class CatbotVision(base.AsyncModule):
    history = {}
    max_history_len = 5

    def __init__(self, enabled=True):
        super().__init__("CatbotVisionModule", base.Module.NATIVE, handler=self.process_first_image)
        self.enabled = enabled
        self.model = None
        self.image_dimensions = (300, 300)

        self.init_model()

    def init_model(self):
        if self.enabled:
            self.model = load_model("models/cat.h5")

    async def process_first_image(self, cmsg):
        result, confidence = False, 1.0
        for attachment in cmsg.discord_msg.attachments:
            if url_has_image(attachment.url):
                data = await attachment.read()
                if data is None or len(data) == 0:
                    continue
                image = Image.open(io.BytesIO(data))
                result, confidence = self.predict_image(cmsg, image)
        print(str(result) + " conf:" + str(confidence))
        if result:
            return base.Action(base.Action.END, reaction=base.EMOJI_CAT)
        return base.NO_MESSAGE_ACTION

    @staticmethod
    def update_history(cmsg, timestamp, processing_time, confidence):
        if cmsg.server_id not in CatbotVision.history:
            CatbotVision.history[cmsg.server_id] = []
        if len(CatbotVision.history[cmsg.server_id]) >= CatbotVision.max_history_len:
            CatbotVision.history[cmsg.server_id] = CatbotVision.history[cmsg.server_id][1:]
        CatbotVision.history[cmsg.server_id].append([timestamp, processing_time, confidence])

    def predict_image(self, cmsg, image):
        timestamp = time.time()
        # Convert it to a Numpy array with target shape.
        max_size = max(image.size)
        x = Image.new("RGB", (max_size, max_size))
        x.paste(image, ((max_size-image.size[0]) // 2,
                        (max_size-image.size[1]) // 2))
        x = x.resize(self.image_dimensions, Image.ANTIALIAS)
        x = np.uint8(np.array(x))
        # Reshape
        x = x.reshape((1,) + x.shape)
        x = x / 255.0
        pred = self.model.predict([x])
        print("pred:", round(pred[0][0], 4), round(pred[0][1], 4))
        result = pred[0][1]
        CatbotVision.update_history(cmsg, timestamp, time.time() - timestamp, result)
        if result > 0.5:
            is_cat = True
        else:
            is_cat = False
            result = 1 - result
        return is_cat, result
