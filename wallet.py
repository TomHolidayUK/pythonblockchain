# Import from pycoin third party package
from Crypto.PublicKey import RSA  # Function for generating keys
from Crypto.Signature import PKCS1_v1_5  # Algorithm for generating signatures
from Crypto.Hash import SHA256
import Crypto.Random
import binascii


class Wallet:
    def __init__(self, node_id):
        # Initialisation of keys
        self.private_key = None
        self.public_key = None
        self.node_id = node_id

    def create_keys(self):
        # Use unpacking from generate_keys
        private_key, public_key = self.generate_keys()
        self.private_key = private_key
        self.public_key = public_key

    def save_keys(self):
        # Store keys to files - public key on top line, private key on bottom line
        # But first check that the keys aren't empty - we don't want to save nothing to a file
        if self.public_key != None and self.private_key != None:
            try:
                with open('wallet-{}.txt'.format(self.node_id), mode='w') as f:
                    f.write(self.public_key)
                    f.write('\n')
                    f.write(self.private_key)
                return True
            # Catch the following error in case the file exists but is empty
            except (IOError, IndexError):
                print('Saving wallet failed')
                return False
        else:
            print('Keys are empty - generate keys before trying to save them')

    def load_keys(self):
        # Import/load keys from wallet.txt
        try:
            with open('wallet-{}.txt'.format(self.node_id), mode='r') as f:
                keys = f.readlines()
                # The public key is the first line on wallet.txt. We need to remove the linebreak charachter which is the last line of the first line (we do this with the range selector [:-1])
                public_key = keys[0][:-1]
                private_key = keys[1]
                self.public_key = public_key
                self.private_key = private_key
            return True
        except (IOError, IndexError):
            print('Loading wallet failed')
            return False

    def generate_keys(self):
        # RSA is a type of key used in blockchain wallets
        private_key = RSA.generate(1024, Crypto.Random.new().read)
        # We get the public key from the private key. In the private key there is a publickey() method
        public_key = private_key.publickey()
        return (binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii'), 
                binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii'))

    # We need methods for creating a signature (assigning a transaction) and one for verifying
    def sign_transaction(self, sender, recipient, amount):
        # Create a signer identity with PKCS1_v1_5
        # We also use RSA to import keys. We need to convert the string keys to binary with binascii.unhexlify()
        # The private key is used for signing
        signer = PKCS1_v1_5.new(RSA.importKey(
            binascii.unhexlify(self.private_key)))
        # We need the payload of what we are going to sign, we store that in a normal hash
        h = SHA256.new((str(sender) + str(recipient) +
                       str(amount)).encode('utf8'))
        # Generate a signature for the transaction
        signature = signer.sign(h)
        return binascii.hexlify(signature).decode('ascii')

    # The following method only requires transaciton so we can use the static method
    @staticmethod
    # Receives whole transaction object because this contains all the data we need to verify
    def verify_transaction(transaction):
        # If the sender is someone esle, we need to verify. But first we need the public key (of the sender) in binary format
        public_key = RSA.importKey(binascii.unhexlify(transaction.sender))
        verifier = PKCS1_v1_5.new(public_key)
        h = SHA256.new((str(transaction.sender) + str(transaction.recipient) +
                       str(transaction.amount)).encode('utf8'))
        return verifier.verify(h, binascii.unhexlify(transaction.signature))


# The public and private key are in binary so we need to convert them to a string, we do this with binascii - this allows us to convert binary data to ASCII

# Problems accessing anaconda packages? On VS code open command pallette and us 'Python: Select Interpreter'
# Also can try the following
# pip3 uninstall PyCrypto
# pip3 install -U PyCryptodome
