import pickle

class PickleSerializer:
    def serialize(self,obj)->bytes:
        return pickle.dumps(obj)
    def deserialize(self,data:bytes):
        return pickle.loads(data)