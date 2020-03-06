import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from keras.models import load_model
from keras_efficientnets import EfficientNetB5
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


class CatbotVision(base.AsyncModule):
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
                result, confidence = self.predict_image(image)
        print(str(result) + " conf:" + str(confidence))
        if result:
            return base.Action(base.Action.END, reaction=base.EMOJI_CAT)
        return base.NO_MESSAGE_ACTION

    def predict_image(self, image):
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
        if result > 0.5:
            is_cat = True
        else:
            is_cat = False
            result = 1 - result
        return is_cat, result
