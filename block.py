from time import time
from utilityfolder.printable import Printable


class Block(Printable):
    # Every blockshould be independent from the other blocks so we use the instance argument
    def __init__(self, index, previous_hash, transactions, proof, time=time()):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = time
        self.transactions = transactions
        self.proof = proof
