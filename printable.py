class Printable:
    # We want to output the transactions as a string and dictionary (not an object)
    # We want to output the block as strings, not objects. So we use __repr__ to define what should be outputted if we print the block
    def __repr__(self):
        return str(self.__dict__)
