import hashlib as hl
import json


def hash_string_256(string):
    return hl.sha256(string).hexdigest()


def hash_block(block):
    """ Hashes a block and returns a string representation of it (the information seperated by -'s)

    Arguments:
        :block: The block that should be hashed
    """
    # Old method for calculating hash
    # return '-'.join([str(block[key]) for key in block])
    # This uses list comprehension to form the hash based on the data of the block

    # New method - An un-readable coded hash for security reasons. The hashed value is still always the same for the same input. 
    # Creating a hash this way also is also shorter so suitable for more data.
    # We can't convert objects to json, therefore we convert the object to a dictionary with __dict__
    # To avoid editing the hash of the previous block (we don't want to do this) we use .copy() - this means we only have
    # the new block
    hashable_block = block.__dict__.copy()
    # Transaction is a list of transaction objects, these can't be converted to strings. These are deeper in the block so aren't 
    # converted by __dict__ to dictionarys
    # Therefore we use the following code to convert the transaction objects to ordered dictionaries with to_ordered_dict()
    hashable_block['transactions'] = [tx.to_ordered_dict()
                                      for tx in hashable_block['transactions']]
    return hash_string_256(json.dumps(hashable_block, sort_keys=True).encode())
    # First we create a string and encode it to 'utf-8' using 'json.dumps(), a string format that can be used by the sha256 
    # algorithm. It is actually yields a binary string. The 64-bit hash that 'haslib.sha256() generates is not a string. 
    # It is a bite-hash, so we use '.hexdigest()' to return a string has with normal charachters. This hash contains all the 
    # information of the block - including the hash of the previous block - this protects the system from unwanted interference.
    # sort_keys=True ensures that the keys of the dictionary are sorted in the same order every time before converting it to a 
    # string. So the same dictionary will always lead to the same string
