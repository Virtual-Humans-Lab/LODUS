# never reuses an id for a given attribute
class IDGen:
    stacks = {}
    
    def __init__(self, attribute, current_id=0):
        self.attribute = attribute
        IDGen.stacks.setdefault(attribute, current_id)

    def get_id(self) -> int:
        current_id = IDGen.stacks[self.attribute]
        IDGen.stacks[self.attribute] += 1
        return current_id
