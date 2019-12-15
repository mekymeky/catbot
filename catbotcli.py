

class CatCLI:
    def __init__(self):
        self.version = "0.0.1"
    
    def reload_message(self):
        return "Loaded CatCLI version " + self.version

    def get_version(self):
        return "Current version: " + self.version

    def handle(self, content):
        if len(content) > 5:
            command = content[5:]

            if command == "version":
                return self.get_version()

        elif content == "!cat":
            return "I'm still a dumb bot, so at the moment, this command does absolutely nothing. But one day, these few letters will conquer the world."


