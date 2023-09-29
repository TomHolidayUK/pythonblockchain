# This will allow a flask application (a server) to be set up which can listen to request and send responses. It will also allow routes / API endpoints
from flask import Flask, jsonify, request, send_from_directory
# Cors is a mechanism that controls that only clients running on the same server can access this server, this is done so that only web pages (HTML pages) returned by a server can again send requests to it.
# However we want to have a setup where other nodes can also connect. This is what the flask_cors package does
from flask_cors import CORS

# Import necessary modules
from wallet import Wallet
from blockchain import Blockchain

app = Flask(__name__)
CORS(app)  # This open the app up to other clients

# Set up an end point (API). app.route() does this - we need to pass the path and the type of request

@app.route('/', methods=['GET'])
def get_node_ui():
    # We want to access the node.html file - this is our user interface
    return send_from_directory('ui', 'node.html')

# Add route for network.html file


@app.route('/network', methods=['GET'])
def get_network_ui():
    # We want to access the node.html file - this is our user interface
    return send_from_directory('ui', 'network.html')

# We need to create and load a wallet


@app.route('/wallet', methods=['POST'])
def create_keys():
    wallet.create_keys()
    # create_keys only initialises the keys. We need to call save_keys to call the keys to a file
    if wallet.save_keys():
        global blockchain
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key': wallet.public_key,
            # The user who creates his private key should be able to know it. So we can return it safely
            'private_key': wallet.private_key,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Saving the keys failed.'
        }
        return jsonify(response), 500


@app.route('/wallet', methods=['GET'])
def load_keys():
    # This function provides a good example of logic we use in other functions in this node.py module
    # Many of the functions called from other classes such as Wallet and Blockchain can fail. In order to output this in a way that is compatible with HTTP requests...
    # ... we return True and False in the called class function. Then in the node file we use a if loop to check if it was successful.
    # If the function is successful we output what we want with a successful status code such as 201.
    # If the function is unsuccessful we output a failure message and an unsuccessful status code such as 500.
    if wallet.load_keys():
        global blockchain
        blockchain = Blockchain(wallet.public_key, port)
        # Below is the same response as create_keys
        response = {
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Loading the keys failed.'
        }
        return jsonify(response), 500


@app.route('/balance', methods=['GET'])
def get_balance():
    balance = blockchain.get_balance()
    if balance != None:
        response = {
            'message': 'Fetched balance successfully.',
            'funds': balance
        }
        return jsonify(response), 200
    else:
        response = {
            'messsage': 'Loading balance failed.',
            'wallet_set_up': wallet.public_key != None
        }
        return jsonify(response), 500


@app.route('/broadcast-transaction', methods=['POST'])
def broadcast_transaction():
    values = request.get_json()
    if not values:
        response = {'message': 'No data found.'}
        return jsonify(response), 400
    # Check for required entries
    required = ['sender', 'recipient', 'amount', 'signature']
    if not all(key in values for key in required):
        response = {'message': 'Some data is missing.'}
        return jsonify(response), 400
    success = blockchain.add_transaction(
        values['recipient'], values['sender'], values['signature'], values['amount'], is_receiving=True)
    if success:
        response = {
            'message': 'Successfully added transaction.',
            'transaction': {
                'sender': values['sender'],
                'recipient': values['recipient'],
                'amount': values['amount'],
                'signature': values['signature']
            },
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Creating a transaction failed.'
        }
        return jsonify(response), 500


# We need to be able to broadcast new block to the peer nodes
@app.route('/broadcast-block', methods=['POST'])
def broadcast_block():
    # We want to add the block onto the blockchain on the peer node
    values = request.get_json()
    if not values:
        response = {'message': 'No data found.'}
        return jsonify(response), 400
    # Check for an absence of a block
    if 'block' not in values:
        response = {'message': 'Some data is missing.'}
        return jsonify(response), 400
    block = values['block']
    # Check the index of the incoming block on the peer node is one higher than the index on the last block on the peer node - this would mean it's 
    # the next block in the chain
    if block['index'] == blockchain.chain[-1].index + 1:
        # Check if adding a block succeeded
        if blockchain.add_block(block):
            response = {'message': 'Block added'}
            return jsonify(response), 201
        else:
            response = {'Message': 'Block seems invalid.'}
            return jsonify(response), 409  # 409 = conflict error
    elif block['index'] > blockchain.chain[-1].index:
        response = {
            'message': 'Blockchain seems to diffe from local blockchain'}
        blockchain.resolve_conflicts = True
        return jsonify(response), 200  # Local problem
    else:
        response = {
            'message': 'Blockchain seems to be shorter, block not added'}
        return jsonify(response), 409


@app.route('/transaction', methods=['POST'])
def add_transaction():
    # First check if there is a valid wallet
    if wallet.public_key == None:
        response = {
            'message': 'No wallet set up.'
        }
        return jsonify(response), 400
    # For this we will call add_transaction from the Blockchain class
    # But there we need to pass some information for the recipient, sender, signature and amount
    # We used to do this in the OLD_node.py by asking the user for input for the recipient and amount. We generated the signature...
    # ... with help from the wallet and then we called add_transaction. We need to do the same in this new node.py file
    # We use the request object from Flask to extract data from an incoming request - this data will be our user inputs
    # This gives us data attached to the incoming request if the data is in JSON format - this will be a requirement - JSON format is necessary
    values = request.get_json()
    # Check if the incoming request has data
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    # Also check if the request data has the following two fields
    required_fields = ['recipient', 'amount']
    # Check for all requests
    if not all(field in values for field in required_fields):
        response = {
            'message': 'Required data is missing.'
        }
        return jsonify(response), 400
    # If we pass the two above checks we know we have all the data we need for the transaction. So now we need a signature
    recipient = values['recipient']
    amount = values['amount']
    # sender = wallet.public_key
    signature = wallet.sign_transaction(wallet.public_key, recipient, amount)
    # Now we have all the data we need to create a new transaction
    success = blockchain.add_transaction(
        recipient, wallet.public_key, signature, amount)
    if success:
        response = {
            'message': 'Successfully added transaction.',
            'transaction': {
                'sender': wallet.public_key,
                'recipient': recipient,
                'amount': amount,
                'signature': signature
            },
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Creating a transaction failed.'
        }
        return jsonify(response), 500


# Now we need to make blockchain related routes - we will return get the blockchain
# This is to mine a block
@app.route('/mine', methods=['POST'])
def mine():
    # We shouldn't mine a block if we have conflicts to resolve. The following if statement checks for that
    if blockchain.resolve_conflicts == True:
        response = {'message': 'Resolve conflicts first, block not added!'}
        return jsonify(response), 409
    block = blockchain.mine_block()
    # Check if block is not equal to None
    if block != None:
        # Need to convert block from objects to dictionary
        dict_block = block.__dict__.copy()
        dict_block['transactions'] = [
            tx.__dict__ for tx in dict_block['transactions']]
        response = {
            'message': 'Block added successfully.',
            'block': dict_block,
            'funds': blockchain.get_balance()
        }
        # 201 = status code that indicates a resources was successfully created
        return jsonify(response), 201
    else:
        response = {
            'message': 'Adding a block failed.',
            'wallet_set_up': wallet.public_key != None
        }
        return jsonify(response), 500  # 500 = service status error code

# Create a request that allows the user to solve conflicts


@app.route('/resolve-conflicts', methods=['POST'])
def resolve_conflicts():
    replaced = blockchain.resolve()
    # Check if it is true that we replaced a chain or not due to conflicts
    if replaced:
        response = {'message': 'Chain was replaced!'}
    else:
        response = {'message': 'Local chain kept!'}
    return jsonify(response), 200  # 200 = successful status code


@app.route('/transactions', methods=['GET'])
def get_open_transaction():
    transactions = blockchain.get_open_transactions()
    # Convert transactions to dictionaries
    dict_transactions = [tx.__dict__ for tx in transactions]
    return jsonify(dict_transactions), 200


@app.route('/chain', methods=['GET'])
def get_chain():
    # Call blockchain from blockchain class
    chain_snapshot = blockchain.chain
    # Now return this to the client (whoever sent the HTTP request). We will send this as JSON data
    # jsonify converts data to JSON
    # But first we need to convert the list of object of chain_snapshot into dictionaries with the following list comprehension
    # we use .copy() in the list comprehension to avoid unexpected side effects when we manipulate the block- it stops future copies from being manipulated
    dict_chain = [block.__dict__.copy() for block in chain_snapshot]
    # We also need to convert the transactions in our block from objects to dictionaries
    for dict_block in dict_chain:
        dict_block['transactions'] = [
            tx.__dict__ for tx in dict_block['transactions']]
    # IMPORTANT - return in flask takes a tuple: the first element is the data of the response and the second element is the HTTP status code (200 = success)
    return jsonify(dict_chain), 200

# This route allows us to add or remove nodes


@app.route('/node', methods=['POST'])
def add_node():
    # Receive the node an as argument
    values = request.get_json()
    # Check if there are valid values
    if not values:
        response = {
            'message': 'No data attached.'
        }
        return jsonify(response), 400
    if 'node' not in values:
        response = {
            'message': 'No data attached.'
        }
        return jsonify(response), 400
    # Now we know we have a good node
    node = values['node']
    blockchain.add_peer_node(node)  # Note - We can do this without a wallet
    response = {
        'message': 'Node added successfully.',
        'all_nodes': blockchain.get_peer_nodes()
    }
    return jsonify(response), 201

# For a DELETE code we add the data to the url not the definition body


@app.route('/node/<node_url>', methods=['DELETE'])
def remove_node(node_url):
    # Check node_url is not empty
    if node_url == '' or node_url == None:
        response = {
            'message': 'No node found.'
        }
        return jsonify(response), 400
    blockchain.remove_peer_node(node_url)
    response = {
        'message': 'Node removed successfully',
        'all_nodes': blockchain.get_peer_nodes()
    }
    return jsonify(response), 200


@app.route('/nodes', methods=['GET'])
def get_nodes():
    nodes = blockchain.get_peer_nodes()
    response = {
        'all_nodes': nodes
    }
    return jsonify(response), 200


if __name__ == '__main__':  # Check we are running it by directly exceuting the file
    # We need to be able to use different ports so the user can run different servers. The following code allows this
    # This is a tool that allows us to parse arguments
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5000)
    args = parser.parse_args()
    port = args.port
    # We also need to vary the name of the .txt file that we save to, so that we don't overwite relevant data
    wallet = Wallet(port)
    blockchain = Blockchain(wallet.public_key, port)
    # run() takes two arguments, the IP on which we want to run and the port on which we want to listen. Arbitrary numbers are placed at first
    app.run(host='0.0.0.0', port=port)

# We need to be able to broadcast information (such as new transaction has been completed or new block has been mined) between nodes


#  * Running on all addresses (0.0.0.0)
#  * Running on http://127.0.0.1:5000
#  * Running on http://192.168.1.97:5000

# python3 node.py
