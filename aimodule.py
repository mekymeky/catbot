import threading
import http.client
import discord.utils

class AIModule():
    def __init__(self):
        self.version = "0.0.1"

    def smartcap(self, text):
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
        return res
                

    def process(self, text):
        response = self.request(text)
        if (response == "#BUSY"):
            return "AI module is busy processing, pls wait <:angelblobcat:618892026284343316>"
        elif (response == "#ERROR"):
            return "AI module error <:blobcatgooglygun:618892026687127552>"
        elif (response == "#INACCESSIBLE"):
            return "AI module inaccessible <:blobcatnotlike:618892026930397214>"
        else:
            response = self.smartcap(response)
            response = response.replace(" i ", " I ")
            response = response.replace(" i'", " I'")
            return response

    def test(self):
        try:
            print("AIM TEST")
            connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=2)
            
            headers = {'Content-type': 'text/plain'}
            connection.request("POST", "/", "#TEST", headers)
            response = connection.getresponse().read().decode()
            print("AIM RES: " + str(response))
            return response == "#OK"
            
        except Exception as ex:
            print(ex)
            return False

    def request(self, text):
        try:
            print("AIM REQ: " + str(text))
            connection = http.client.HTTPConnection("127.0.0.1", 8000)
            headers = {'Content-type': 'text/plain'}
            connection.request("POST", "/", text, headers)
            response = connection.getresponse().read().decode()
            print("AIM RES: " + str(response))
            return response
            
        except Exception as ex:
            print(ex)
            return "#INACCESSIBLE"
