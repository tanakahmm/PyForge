import pickle


class Demo:
    def __init__(self):
        self.name = "PyForge"
        self.file = open("/tmp/demo.txt", "w")

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["file"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.file = open("/tmp/demo.txt", "a")


obj = Demo()

data = pickle.dumps(obj)

print("Serialized:", data)
restored = pickle.loads(data)

print("Name:", restored.name)
print("File:", restored.file)

restored.file.write("Hello from restored object\n")
restored.file.close()