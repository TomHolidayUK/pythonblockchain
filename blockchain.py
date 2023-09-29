# python3 blockchain.py

from functools import reduce
import hashlib as hl
import json
import pickle
import requests

# Import a function from our hash_util.py file. Omit the ".py" in the import
from utilityfolder.hash_util import hash_block
from utilityfolder.verification import Verification
# Import Block class
from block import Block
from transaction import Transaction
from wallet import Wallet


# The reward we give to miners (for creating a new block)
MINING_REWARD = 10

# Create a class for the blockchain, which we can use to create a blockchain object which can be used in the Node class.


class Blockchain:
    # Constructor
    def __init__(self, public_key, node_id):
        # Our starting block for the blockchain
        # Create this from the Block class and give starting criteria for previous_hash, index, transactions, proof and timestamp
        genesis_block = Block(0, '', [], 100, 0)
        # Initiliasing our (empty) blockhain list
        # We add __ before an attribute to mark it as private. We can do this with the chain and open_transaction attributes so that they aren't manipulated from the outside. This has security benefits
        self.chain = [genesis_block]
        # The blockchain should only be editable from inside the blockchain, not outside
        # Unhandled transcations
        self.__open_transactions = []
        self.public_key = public_key
        # Add instance attribute for peer node and initialise an empty set. We can add and remove nodes to this set
        # Sets in python are unordered, unchangeable and unindexed. Also they don't allow duplicate values so every node can only be added once - this is good
        self.__peer_nodes = set()
        self.node_id = node_id
        self.resolve_conflicts = False
        # Load data after empty set of nodes initiliased so that it is always updated
        self.load_data()

    # We add the following two methods to return copies of reference objects for chain and open_transactions so that we can't take advantage of that reference by still editing it from the outside after getting access to it
    # When you try to get the value of chain / access chain the following is achieved
    @property
    def chain(self):
        return self.__chain[:]

    # When we want to set something to chain (overwrite it - like in the load_data function) the following happens ??
    @chain.setter
    def chain(self, val):
        self.__chain = val

    def get_open_transactions(self):
        return self.__open_transactions[:]

    def load_data(self):  # load_data is a method of the Blockchain class
        # We need to acces the global variables for blockchain and open_transactions
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='r') as f:
                # with open('blockchain.txt', mode='r') as f:
                # We use .json or .pickle to convert the data to a string (when we write) and then back to a native python object, such as a list 
                # (when we read)
                #file_content = pickle.loads(f.read())
                file_content = f.readlines()
                blockchain = json.loads(file_content[0][:-1])
                # When we load our transactions we need to load them as OrderedDicts - because when we add a transaction we add it as an OrderedDict
                # Therefore we need to ovewrite the old loaded data 'blockchain' with new data for the transactions
                # Go through all transactions for a given block and create an OrderedDict for all of them so that this gets stored in the block instead 
                # of the original transaction
                updated_blockchain = []
                for block in blockchain:
                    # Store list of transaction in seperate variable converted_tx to make code look neater
                    # Transaction needs to be an object not and OrderedDict but we also want to use an OpenDict to ensure we don't run into issues when 
                    # hashing
                    converted_tx = [Transaction(
                        tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']]
                    updated_block = Block(
                        block['index'], block['previous_hash'], converted_tx, block['proof'], block['timestamp'])
                    updated_blockchain.append(updated_block)
                # Update blockchain
                self.chain = updated_blockchain
                open_transactions = json.loads(file_content[1][:-1])
                # We also need to build the open_transaction load method upon OrderedDicts
                updated_transactions = []
                for tx in open_transactions:
                    updated_transaction = Transaction(
                        tx['sender'], tx['recipient'], tx['signature'], tx['amount'])
                    updated_transactions.append(updated_transaction)
                # Store updated/loaded transactions
                self.__open_transactions = updated_transactions
                # Load connected nodes
                # Index third line of blockchain.txt with [2]
                peer_nodes = json.loads(file_content[2])
                # Store loaded nodes in a set
                self.__peer_nodes = set(peer_nodes)
        except (IOError, IndexError):
            # Sometimes we can't control if we can access the file or not. So we handle this file error with IOError
            # We also add Index Error in case that blockchain.txt is empty
            # This hardcodes the starting data so it is available if we can't read the data file
            print('Handled exception...')
        finally:
            print('Cleanup!')

    def save_data(self):
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='w') as f:
                # We can't convert objects to json, therefore we convert the object to a dictionary with __dict__
                # We are not manipulating this dictionary so we don't need .copy()
                # We need to insure the transactions are converted to dictionaries
                # block_el.transactions is the list of transactions sotred in a block which gets converted to a dictionary, 
                # this the get stored in a block, and then a list of block which is also converted to a dictionary
                saveable_chain = [block.__dict__ for block in [Block(block_el.index, block_el.previous_hash, [
                    tx.__dict__ for tx in block_el.transactions], block_el.proof, block_el.timestamp) for block_el in self.__chain]]
                f.write(json.dumps(saveable_chain))
                f.write('\n')
                # We need to convert the objects of open_transactions to a dictionary
                saveable_tx = [tx.__dict__ for tx in self.__open_transactions]
                f.write(json.dumps(saveable_tx))
                f.write('\n')
                # Write connected nodes to file
                f.write(json.dumps(list(self.__peer_nodes)))
                # save_data = {
                #     'chain': blockchain,
                #     'ot': open_transactions
                # }
                # f.write(pickle.dumps(save_data))
        except IOError:
            print('Saving failed!')

    def proof_of_work(self):
        """ Increment through different proof numbers to find a valid PoW for our criteria """
        # Fetch the last block - [-1] selects a list element from the right (the last block)
        last_block = self.__chain[-1]
        # Calculate last hash
        last_hash = hash_block(last_block)
        # Increment through proof numbers until the valid_proof function is satisfied. Output valid proof number
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof

    def get_balance(self, sender=None):
        """ Get the amount for a given transaction for all the transactions in a block if the sender of that transaction is the participant - do this for all blocks in the blockchain 

        Arguments: participant: The person for whom to calculate the balance
        """
        # If there is no sender, the partipant should be the public key
        if sender == None:
            # This code can fail if we have no registered public key. Thereofre the following if statement checks for this so that the get_balance function in the Node calss can notify the user
            if self.public_key == None:
                return None
            participant = self.public_key
        else:
            # We want the participant to bethe same as the sender - therefore it doesn't matter which node you are sending from, the sender will always be the same
            participant = sender

        # Fetch a list of all sent coin amounts for the given person
        # This fetches sent amounts of transaction that were already included in the block
        tx_sender = [[tx.amount for tx in block.transactions
                      if tx.sender == participant] for block in self.__chain]
        # Fetch a list of all sent coin amounts for the given person
        # This fetches sent amounts of open transactions (to avoid double spending)
        open_tx_sender = [tx.amount
                          for tx in self.__open_transactions if tx.sender == participant]
        # This gives a list with the transactions on the blockchain + open transactions - this is what we have paid in the past and what we are trying to pay now
        tx_sender.append(open_tx_sender)
        print(tx_sender)
        amount_sent = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                             if len(tx_amt) > 0 else tx_sum + 0, tx_sender, 0)
        # This fetches recieved coin amounts of transactions that were already in...
        # We ignore open transactions here because you shouldn't be able to...
        # This uses the reduce tool to condense the following code into one line

        # Old code
        # amount_sent = 0
        # for tx in tx_sender:
        #    if len(tx) > 0: # This means the code ignores the genesis block
        #        amount_sent += tx[0]

        # This fetches recieved coin amounts of transactions that were already included in blocks of the blockchain
        # We ignore open transactions here because you shouldn't be able to spend coins before the transaction was confirmed
        tx_recipient = [[tx.amount for tx in block.transactions
                        if tx.recipient == participant] for block in self.__chain]
        amount_received = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                                 if len(tx_amt) > 0 else tx_sum + 0, tx_recipient, 0)
        # This also uses the reduce tool to condense the following code into one line

        # Old code
        # amount_received = 0
        # for tx in tx_recipient:
        #    if len(tx) > 0:
        #        amount_received += tx[0]

        # Return the total balance
        return amount_received - amount_sent

    def get_last_blockchain_value(self):
        """ Returns the last value of the current blockchain """
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]

    def add_transaction(self, recipient, sender, signature, amount=1.0, is_receiving=False):
        """ Appends a new value as well as the last blockchain value to the blockchain

        Arguments:
            :sender: the sender of the coins
            :recipient: the recipiento of the coins
            :signature: The signature of the transaction.
            :amount: the amount of coins sent with the transaction, default is 1 coin
        """
        # We should check that in the hosting_node a public key that is not None is stored - A public key should be needed to run the file.
        # Without the following code this can be avoided by passing None for the public and private key into the Wallet() and Blockchain. This should be prevented
        # if self.public_key == None:
        #     return False
        transaction = Transaction(sender, recipient, signature, amount)
        # Transaction dictionary contains all data of the transaction
        if Verification.verify_transaction(transaction, self.get_balance):
            # This process adds transaction data to open transactions
            self.__open_transactions.append(transaction)
            self.save_data()
            # We can either be creating a new transaction or receiving a broadcast. We only want to broadcast the transaction if we are adding a 
            # transaction. If we are receiving then we don't want to broadcast as this can cause an infinite number of broadcast between nodes. 
            # Therefore we use the following if loop:
            if not is_receiving:
                # At this point after saving the data, it would be a good place to broadcast this data to the other peer nodes
                for node in self.__peer_nodes:
                    # Each node is on a different server so we need to send a HTTP request to send data
                    url = 'http://{}/broadcast-transaction'.format(node)
                    # We could fail to make a connection to a peer node - we can't predict when it will fail so we use a try block
                    try:
                        # Send a HTTP post request with requests
                        response = requests.post(url, json={
                                                 'sender': sender, 'recipient': recipient, 'amount': amount, 'signature': signature})
                        # Check for errors
                        if response.status_code == 400 or response.status_code == 500:
                            print('Transaction declined: Needs resolving')
                            return False
                    except requests.exceptions.ConnectionError:
                        continue
            return True
        return False

# Generate PoW and add it to the mine_block metadata

    def mine_block(self):
        """ This takes all open transactions and adds to a block (and then then blockchain) - it procesess open transactions """
        if self.public_key == None:
            return None
        # Fetch the current last block of the blockchain
        last_block = self.__chain[-1]
        # Hash the last block (to be able to compare it to the stored value and verify it)
        hashed_block = hash_block(last_block)
        # Fetch valid PoW for the current block
        proof = self.proof_of_work()
        # Miners should be rewarded, so let's create a reward transaction
        reward_transaction = Transaction(
            'MINING', self.public_key, '', MINING_REWARD)
        # The following 2 lines ensures that reward_transactions is managed locally, this means the global variable open_transactions wouldn't 
        # be affected if mine_block denies a transaction - we don't want to add a reward if the transaction doesn't completely process
        # Copy transaction instead of manipulating the open_transactions
        # This ensures that if or some reason the mining should fail,we don't...
        # This returns a new list (and doesn't affect the orignal list) - Refer to Lesson 78
        copied_transactions = self.__open_transactions[:]
        # After we have constructed our block objects we want to verify the signature for every transaction (except the reward transaction) with 
        # the following code:
        for tx in copied_transactions:
            if not Wallet.verify_transaction(tx):
                return None
        copied_transactions.append(reward_transaction)
        # open_transactions.append(reward_transaction)
        block = Block(len(self.__chain), hashed_block,
                      copied_transactions, proof)
        self.__chain.append(block)
        self.__open_transactions = []
        self.save_data()
        # Now we need to inform he peer nodes if there is a new block
        for node in self.__peer_nodes:
            url = 'http://{}/broadcast-block'.format(node)
            # Convert block to a dictionary
            converted_block = block.__dict__.copy()
            converted_block['transactions'] = [
                tx.__dict__ for tx in converted_block['transactions']]
            # The data we want to append is a dictionary with the block key
            try:
                response = requests.post(url, json={'block': converted_block})
                if response.status_code == 400 or response.status_code == 500:
                    print('Block declined: Needs resolving')
                # If status code = 409 we need to resolve conflicts
                if response.status_code == 409:
                    self.resolve_conflicts = True
            except requests.exceptions.ConnectionError:
                continue
        return block

    # mine_block mines a new block with a reward. We want a function just to add a block (NOT to mine a block)
    def add_block(self, block):
        # Extract transaction data from transaction dictionary in block (block['transaction']) then create a list of all these transactions so 
        # we can later pass it to valid_proof
        transactions = [Transaction(
            tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']]
        proof_is_valid = Verification.valid_proof(
            transactions[:-1], block['previous_hash'], block['proof'])  # To ignore the reward transaction we use transaction[:-1]
        # Check if in the peer nodes blockchain the hash of the last block matches the hash stored in the last block of the incoming block
        hashes_match = hash_block(self.chain[-1]) == block['previous_hash']
        # Combine the above checks in a if statement
        if not proof_is_valid or not hashes_match:
            return False
        # If we pass all the above checks we now know it is safe to add a block
        # First we need to create a block object
        converted_block = Block(
            block['index'], block['previous_hash'], transactions, block['proof'], block['timestamp'])
        self.__chain.append(block)
        # We need to also update open_transactions
        stored_transactions = self.__open_transactions[:]
        # Loop through incoming transactions (itx)
        for itx in block['transactions']:
            for opentx in stored_transactions:
                # For every incoming transaction check if its part of open transactions
                # Also check if sender, recipient, amount and signature are the same in the open transactions and incoming transactions
                if opentx.sender == itx['sender'] and opentx.recipient == itx['recipient'] and \
                    opentx.amount == itx['amount'] and opentx.signature == itx['signature']:
                    # If they are equal try to remove it
                    try:
                        self.__open_transactions.remove(opentx)
                    except ValueError:
                        print('Item was already removed')
        self.save_data  # Update the stored data for the peer node
        return True

    # Resolve conflicts using the theory that the node with the longest chain always wins
    def resolve(self):
        winner_chain = self.chain
        # Control whether our current chain is getting replaced. Initially we assume it is not
        replace = False
        # Go through all nodes in peer nodes to get snapshot of the block chain on each peer node
        for node in self.__peer_nodes:
            # Call the chain of peer nodes with the following URL - this calls the GET /chain route
            url = 'http://{}/chain'.format(node)
            try:
                # Try to send a request to the url
                response = requests.get(url)
                # Now lets see whats in the request response - extract data as json
                node_chain = response.json()
                # We have a list, using nested list comprehension create a new list of block objects - use the Block constructor.
                # Then where we add transactions we need a list comprehension where we create a new list of transactions
                node_chain = [Block(block['index'], block['previous_hash'], [Transaction(
                    tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']],
                    block['proof'], block['timestamp']) for block in node_chain]
                # Create node chain that is a list of blocks which has transactions that are transaction objects
                node_chain_length = len(node_chain)
                local_chain_length = len(winner_chain)
                # We need to find out if the chain of the other peer node is longer than the current chain and if it's valid
                if node_chain_length > local_chain_length and Verification.verify_chain(node_chain):
                    # Make the longest chain the winner chain
                    winner_chain = node_chain
                    replace = True
            except requests.exceptions.ConnectionError:
                continue
        self.resolve_conflicts = False
        self.chain = winner_chain
        # If we are replacing our blockchain then we can assume all of our open transactions are incorrect. Therefore we need to reset them
        if replace:
            self.__open_transactions = []
        self.save_data()
        return replace

    def add_peer_node(self, node):
        """Adds a new node to the peer node set.

        Arguments:
            :node: The node URL which should be added.
        """
        # Access peer_nodes and add a node
        self.__peer_nodes.add(node)
        # Save connected nodes list to local blockchain.txt file
        self.save_data()

    def remove_peer_node(self, node):
        """Removes a new node to the peer node set.

        Arguments:
            :node: The node URL which should be removed.
        """
        self.__peer_nodes.discard(node)
        self.save_data()

    def get_peer_nodes(self):
        """Return a list of all connected peer nodes."""
        return list(self.__peer_nodes)


# Notes

# Before making transactions the user needs to build up their balance, they can do this by mining. This mirrors how a real blockchain system work in terms of rewarding miners.

# Resolving conflicts
# Different nodes can mine blocks independently and broadcast these to other nodes so they are also added
# But this can lead to conflicts where different nodes have different lengths
# This system is designed that when it notices this has happedn it will resolve these conflicts. because we want the blockchain to be consistent and consistent across all nodes
# Therefore we use a system where the longest current chain on whatever node wins the conflict and becomes the chosen new blockchain
# If a chain is manipulated on a node this will be detected and the chains on the other nodes will never be replaced

# HTTP
# The system will accept HTTP requests and send HTTP responses
# The HTTP request will use an IP address instead of a domain name
# There are different types of HTTP requests (POST, GET, DELETE etc)
# There are two types of data format for HTTP requests: HTML and JSON

# Hashing
# We use hashes to summarise the information of a block. Each block contains the hash of its previous block (previous_hash). This prevents the blockchain from being manipulated and verifies the system.
# We're not using a Hash because we want to hide the values. We could do this with a Hash but that's not the idea of a Blockchain. All the data should be publicly available, we don't want to hide the Block data - everyone should be able to check and validate the Blockchain.

# Proof of work
# Proof of work makes mining blocks challenging - it should be challenging - require time and hardware resources)!
# This allows us to control the speed of coins enetering our network but more importantly provides security by ensuring you can't edit the entire blockchain
# With just the hashing method, you could in-theory edit a block and all the susquent hashes to hack the blockchain. Proof of work ensures this isn't possible
# PoW is just a number, but it's a number which, together with other input data (transactions and previous hash), yields a hash that suffices a condition defined by us (=> the creators of the blockchain).
# The hash we use here is different to previous_hash! We're simply using a hash for this check since it's convenient to check starting characters of a fixed-length (always 64 characters for SHA256) string.
# A typical requirement is for the hash to start with X 0s (though you can come up with any condition of your choice). The more 0s we require, the longer it'll take to find a fitting PoW number - that's why for Bitcoin it can take multiple years to generate new block.
# And only if these three inputs yield a hash that starts with two 0s, we accept the hash and therefore the PoW. Since the transactions of the next block as well as the previous block's hash are static, only the PoW is adjusted until a matching hash is found.
# The guessed (and fitting) PoW is then also stored in the mined block.
# Other nodes can then easily confirm or deny the validity of the block since they just have to create a hash from the three input values (which are all known as they are included in the block). If the PoW doesn't lead to a valid hash, the block is not treated as valid and hence the overall chain is not accepted.
# If some node tries to cheat, manipulating a block's transactions + the subsequent blocks previous_hash values would NOT suffice anymore.
# For changed transactions and/ or previous_hash values, the old PoW wouldn't yield a valid PoW-hash anymore. A cheater would therefore have to re-calculate all PoW numbers for all subsequent blocks.
# "Honest nodes" on the other hand only need to mine one new block in the time the cheater takes to re-calculate potentially dozens of blocks to render the cheater's chain invalid.
# That's how PoW secures the blockchain - PoW is essentially another calculation

# There are 3 layers of blockchain security built into this programme:
# 1 - The blocks knowing each other - this prevent basic block manipulation
# 2 - Proof of work - no mass-manipulation possible
# 3 - Public and Private key - transaction data needs to be signed via signature verification

# Transaction - dictionary
# List of transactions - list
# Blockchain - list [order + mutuable]

# A black - dictionary (could also be a tuple)
# List of participants - set [we need unique values]

# 'join' can be used to insert something inbetween every value of a list. '-'.join is useful to make lists look neat.

# The Python Tutorial
# https://docs.python.org/3/tutorial/index.html
# https://docs.python.org/3.4/library/index.html
# The Python standard Library
# https://docs.python.org/3/library/index.html
# Use help() to get the interactive help utility

# python3 blockchain.py
