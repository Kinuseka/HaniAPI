"""Module for formatting strings"""
class Prettify:
    def __init__(self) -> None:
        self.state = []
        self.headers = []
        self.texts = []
        self.arranged = []
        self._head_val = 1
        self._text_val = 0
        self._cache_val = None

    def add_tab(self,data="",lines=30):
        format = f"{data:=^{lines}}"
        self.headers.append(format)
        self.state.append(self._head_val)

    def add_line(self,data=""):
        self.texts.append(data)
        self.state.append(self._text_val)

    def add_sort(self,key="",value="",align=1):
        key = '%s:' % key
        format = f"{key:{len(key) + align}}{value}"
        self.texts.append(format)
        self.state.append(self._text_val)
    
    def return_states(self) -> list: #List of sorted arguments
        if self.arranged != []:
            return self.arranged

    def prettyprint(self):
        for text in self._sort_data():
            print(text)

    def prettystring(self):
        curr = ""
        for text in self._sort_data():
            try:
                curr += text + "\n"
            except TypeError:
                pass
        return curr

    def _sort_data(self):
        track_head = 0
        track_text = 0
        for i in self.state:
            if i:
                self.arranged.append(self.headers[track_head])
                track_head += 1
            elif not i:
                self.arranged.append(self.texts[track_text])
                track_text += 1
        return self.arranged