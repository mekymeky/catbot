import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import tensorflow as tf
import catbot.botbase as base
from catbot.ai.tokenization import FullTokenizer, mb_preprocess_text


class CatbotSentiment(base.AsyncModule):

    OUTPUT_TENSOR = 3817

    def __init__(self, enabled=True):
        super().__init__("CatbotSentimentModule", base.Module.NATIVE, handler=self.process_text)
        self.enabled = enabled
        self.interpreter = None
        self.tokenizer = None

        self.init_model()

    def init_model(self):
        if self.enabled:
            self.interpreter = tf.lite.Interpreter("models/sentiment/model.tflite")
            self.interpreter.allocate_tensors()
            self.tokenizer = FullTokenizer("models/sentiment/vocab")

    async def process_text(self, cmsg):
        if not self.enabled:
            await cmsg.respond("Experimental sentiment module is disabled.")
            return
        text = cmsg.raw
        text = text[text.index("exp_s") + 5:]
        text = text.strip()

        inputs = mb_preprocess_text(text, self.tokenizer)
        self.interpreter.set_tensor(0, inputs[0])
        self.interpreter.set_tensor(1, inputs[1])
        self.interpreter.set_tensor(2, inputs[2])
        outputs = self.interpreter.get_tensor(CatbotSentiment.OUTPUT_TENSOR)[0]

        await cmsg.respond(
            f"Output tensor: [{base.EMOJI_AMGR} {outputs[0]}, {base.EMOJI_BLOBCATPRETTYGOOD} {outputs[1]}]"
        )

