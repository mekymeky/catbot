import discord
from urllib.parse import quote

import catbot.botbase as base
from catbot.botbase import CMD


class CatbotTTS:
    def __init__(self):
        self.base_url = "http://localhost:5002/api/tts"

    def build_request_url(self, text):
        return self.base_url + "?text=" + quote(text) + "&speaker_id=p270&style_wav="


class CatbotVoice(base.AsyncModule):
    connected_channels = {}

    def __init__(self, enabled=True):
        super().__init__("CatbotVisionModule", base.Module.NATIVE, handler=self.process_message)
        self.enabled = enabled
        self.tts = CatbotTTS()

    async def process_message(self, cmsg):
        msg = cmsg.raw_lower
        if msg.startswith(CMD + "voice connect"):
            await self.join_channel(cmsg)
        elif msg.startswith(CMD + "voice disconnect"):
            await self.leave_channel(cmsg)
        elif msg.startswith(CMD + "tts"):
            await self.speak(cmsg)
        else:
            await cmsg.respond("Error: Unknown command type for the voice module.")

    async def join_channel(self, cmsg):
        if not self.enabled:
            return
        voice = self.connected_channels.get(cmsg.server_id, None)
        if voice is not None:
            try:
                base.LOGGER.info("Already have an active channel, attempting to disconnect")
                await voice.disconnect()
            except Exception as err:
                base.LOGGER.warn(err)
        if cmsg.author_voice_channel is None:
            await cmsg.respond("Error: I can't see you in any voice channel.")
        else:
            voice = await cmsg.author_voice_channel.connect()
            self.connected_channels[cmsg.server_id] = voice
        base.LOGGER.debug("Connected channels:", self.connected_channels)

    async def leave_channel(self, cmsg):
        if not self.enabled:
            return
        voice = self.connected_channels.get(cmsg.server_id, None)
        if voice is not None:
            try:
                await voice.disconnect()
            except Exception as err:
                base.LOGGER.warn(err)
        else:
            await cmsg.respond("Error: I don't think I'm in any voice channel.")
        base.LOGGER.debug("Connected channels:", self.connected_channels)

    async def speak(self, cmsg):
        if not self.enabled:
            return
        base.LOGGER.debug("Connected channels:", self.connected_channels)
        voice = self.connected_channels.get(cmsg.server_id, None)
        if voice is None:
            await cmsg.respond("Error: I don't think I'm in any voice channel.")
        else:
            # remove prefix
            prefix_len = len(CMD) + 4 # len("$cat$tts ")
            text = cmsg.raw[prefix_len:].strip()
            voice.play(discord.FFmpegPCMAudio(self.tts.build_request_url(text)))
            # sleep while audio is playing.
            while voice.is_playing():
                await cmsg.sleep(.33)
