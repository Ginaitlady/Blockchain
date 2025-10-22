Simple Blockchain in Python
This project is a simple implementation of a cryptocurrency blockchain created for educational purposes, based on the popular tutorial "Learn Blockchains by Building One".

It covers the fundamental concepts of blockchain technology, including proof-of-work, transactions, and a consensus algorithm for resolving conflicts in a decentralized network. The entire blockchain is accessible via an HTTP API built with Flask.

## Features
Proof of Work Algorithm: A simple algorithm to secure the network by making block creation computationally difficult.

Transactions: The ability to create new transactions for "sending" currency between parties.

Decentralized Consensus: Implements a basic consensus algorithm that replaces any chain on a node with the longest valid chain on the network.

HTTP API: A Flask-based API with endpoints to:

Mine new blocks (/mine)

Create new transactions (/transactions/new)

View the full blockchain (/chain)

Register new nodes in the network (/nodes/register)

Resolve conflicts between nodes (/nodes/resolve)

## How to Run
### Prerequisites
Python 3.9+

Conda (or any other virtual environment manager)

Postman (for testing the API)

### 1. Set Up the Environment
First, create and activate a new conda environment to ensure all dependencies are handled correctly.

Bash

# Create a new environment with Python 3.9
conda create --name blockchain-env python=3.9

# Activate the environment
conda activate blockchain-env
### 2. Install Dependencies
Install the required Python libraries using pip.

Bash

pip install Flask requests
### 3. Run a Single Node
To start a single blockchain node, run the following command in your terminal:

Bash

python blockchain.py
The server will start on http://localhost:5000.

### 4. Run Multiple Nodes (for Consensus Testing)
To test the decentralized nature of the blockchain, you can run multiple nodes on different ports. Open a new terminal window for each additional node.

Bash

# Terminal 1 (Node 1)
python blockchain.py --port 5000

# Terminal 2 (Node 2)
python blockchain.py --port 5001
## Testing the API with Postman
You can use a tool like Postman to interact with the blockchain's API endpoints.

Create a Transaction: Send a POST request to {{address}}/transactions/new with a JSON body:

JSON

{
 "sender": "my-address",
 "recipient": "another-address",
 "amount": 5
}
Mine a Block: Send a GET request to {{address}}/mine. This will mine a new block, including any pending transactions, and add it to the chain.

View the Chain: Send a GET request to {{address}}/chain to see the entire blockchain.

Register a Node: Send a POST request to {{address}}/nodes/register to inform a node about other nodes on the network.

JSON

{
 "nodes": ["http://localhost:5001"]
}
Resolve Conflicts: Send a GET request to {{address}}/nodes/resolve to run the consensus algorithm. The node will check other registered nodes and replace its chain if it finds a longer valid one.
