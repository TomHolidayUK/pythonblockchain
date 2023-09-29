""" Provides verification helper methods. """

# This class acts as a helper/container class of verification functions, it isn't used to create objects like other classes

# Import two functions from our hash_util.py file. Omit the ".py" in the import
from utilityfolder.hash_util import hash_string_256, hash_block
from wallet import Wallet


class Verification:
    """ A helper class which offers various static and class-based verification functions. """
    # valid_proof only works with the inputs it's given (transactions, last_hash and proof) - it's not accessing anything from 
    # the class, therefore we can use a static method
    @staticmethod
    # ALL CLASS METHODS NEED TO ACCEPT 'SELF'
    def valid_proof(transactions, last_hash, proof):
        """ This generates a new hash and checks whether it fulfills our difficulty criteria for Proof of Work 

        Arguments: transactions: transactions of the new block to be generated 
                : last_hash: the hash of the previous block in the chain
                : proof: the Proof of Work number (nonce)
        """
        # Make a string of all necessary data. encode to utf-8.
        guess = (str([tx.to_ordered_dict() for tx in transactions]
                     ) + str(last_hash) + str(proof)).encode()
        # Create a hash
        # IMPORTANT: This is not the same has as will be stored in previous_hash
        guess_hash = hash_string_256(guess)
        # Check if this hash fulfills our condition - if the PoW number (proof) is valid
        # print(guess_hash)
        return guess_hash[0:2] == '00'

    # verify_chain uses valid_proof - therefore we need access to the chain, but we don't need an instance so we can use a class method
    @classmethod
    def verify_chain(cls, blockchain):
        """ Verify the current blockchain and return True if it's Valid and False if it's not.
        Compare the stored hash in a given block with the re-calculated hash of the previous block
        Also check PoW is valid using valid_proof """
        for (index, block) in enumerate(blockchain):
            if index == 0:
                continue
            if block.previous_hash != hash_block(blockchain[index - 1]):
                return False
            # In the following PoW validation we need to exclude the reward transaction because in mine_block the reward is included after the calculation of proof
            # Using the range selector [:-1] selects all elements except the final one
            # valid_proof is form a different class so we need .self
            if not cls.valid_proof(block.transactions[:-1], block.previous_hash, block.proof):
                print('Proof of work is invalid')
                return False
        return True

    @staticmethod
    # get_balance is in the main blockchain.py code so we need to call it as an argument - a reference to the function
    def verify_transaction(transaction, get_balance, check_funds=True):
        """ Verify the sender can afford the requested transaction 

        Arguments: transaction: The transaction that should be verified.
        """
        # When we add a transaction with add_transaction we verify with verify_transaction from the Verification class to check there are available funds
        # But when we run node.py we try to verify with verify_transactions (NOT verify_transaction) and this is excectured on open_transactions so it doesn't matter if we have available funds because we are already past that point
        # We want to verify funds and the signature at the same time. We do this with the following if statement
        if check_funds:
            sender_balance = get_balance(transaction.sender)
            # Check the sender has sufficient funds as well as checking the signature is correct using verify_transaciton form the Wallet class
            return sender_balance >= transaction.amount and Wallet.verify_transaction(transaction)
        else:
            # Only check the signature
            # We pass False in verify_transactions to execute this else code
            return Wallet.verify_transaction(transaction)
    # This function accepts two arguments
    # One required one (transactional_amount) and one optional one (last_transaction)
    # last_transaction is optional because it has a default value => [1]

    @classmethod
    def verify_transactions(cls, open_transactions, get_balance):
        # All transactions need to be true
        # This is a second safety precuation as verify_transaction already "verifies that the sender can afford the requested transaction"
        return all([cls.verify_transaction(tx, get_balance, False) for tx in open_transactions])
