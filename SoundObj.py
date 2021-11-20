class Sound:
    def __init__(self, name, file, desc, url):
        self.name = name
        self.file = file
        self.desc = desc
        self.url = url

    def __str__(self):
        return f'{{"name": {self.name}, "file": {self.file}, "desc": {self.desc}, "url": {self.url}}}'