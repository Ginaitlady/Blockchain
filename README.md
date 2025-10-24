==========================================================
Simple Blockchain in Python
==========================================================
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


==========================================================
🐍 SnakeCoin: A Simple Proof-of-Work Blockchain in Python
==========================================================

This project is an educational implementation of a simple cryptocurrency blockchain, written in Python. It is based on the popular "Let's Build the Tiniest Blockchain" article, but has been significantly enhanced to include a more secure Proof-of-Work algorithm and a robust consensus mechanism.

This application runs as a networked Flask server (a "node") that can communicate with other nodes. It allows users to submit transactions, mine new blocks (and earn rewards), and resolve conflicts between different versions of the chain across the network.

Features
Flask API: Runs as a web server with API endpoints to interact with the blockchain.

SHA-256 Proof-of-Work (PoW): A secure, difficulty-based mining algorithm (instead of a simple division problem). Miners must find a hash starting with a specific number of zeros.

Mining & Rewards: A /mine endpoint that bundles transactions and grants the miner a reward (from the "network") for finding the proof.

Transaction Pool (Mempool): New transactions are held in a pool until they are included in the next mined block.

Decentralized Consensus: Implements a "Longest Valid Chain" rule. Nodes can query their peers and update their own chain if a peer has a longer, and valid, chain.

Chain Validation: A robust is_chain_valid function that checks the integrity of an entire chain by:

Verifying each block's previous_hash matches the hash of the block before it.

Verifying the PoW (nonce) for every block is correct.

How It Works
The Block
Each Block in the chain is a Python class containing:

index: The block's height in the chain.

timestamp: Time of creation.

data: A dictionary holding:

transactions: A list of all transactions included in this block.

nonce: The "magic number" found during mining that solves the Proof-of-Work.

previous_hash: The SHA-256 hash of the preceding block, linking the chain together.

hash: The SHA-256 hash of this block's contents (calculated after creation, though this implementation simplifies it).

Proof-of-Work (PoW)
To add a new block (i.e., "mine"), a node must find a nonce (a number, starting from 0) such that when the nonce is hashed with the previous block's hash and the new transactions, the resulting SHA-256 hash begins with a specific number of zeros.

This DIFFICULTY is set as a global variable (e.g., DIFFICULTY = 4 means the hash must start with "0000").

Python

# The core PoW logic
target = '0' * DIFFICULTY
while True:
    data_to_hash = (str(last_block_hash) + 
                    str(transactions) + 
                    str(nonce))
    guess_hash = hasher.sha256(data_to_hash.encode('utf-8')).hexdigest()
    
    if guess_hash.startswith(target):
        return nonce, guess_hash # Found it!
    nonce += 1
This process is computationally "hard" (takes time and electricity) but "easy" for other nodes to verify, which secures the network.

Consensus Algorithm
This is the key to decentralization. When a node's chain conflicts with another, the network "votes" by following the Longest Valid Chain Rule.

A node calls the /consensus endpoint.

The node requests the full blockchains from all other nodes in its peer_nodes list (using GET /blocks).

It compares its own chain length to the chains it received.

If it finds a chain that is both longer and valid (checked with is_chain_valid), it replaces its own local chain with the new, longer one.

Technology Stack
Python 3.x

Flask: For creating the web server and API endpoints.

Requests: For communication between nodes (in the consensus function).

Setup & Installation
Clone the repository:

Bash

git clone <your-repo-url>
cd <your-repo-name>
Create a virtual environment (recommended):

Bash

# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
Install dependencies:

Bash

pip install -r requirements.txt
(If you don't have a requirements.txt, just install Flask and Requests):

Bash

pip install flask requests
How to Use: API Endpoints
Once the server is running (e.g., python snakecoin.py 5000), you can interact with it using any API client like Postman or cURL.

POST /txion
Submits a new transaction to this node's transaction pool.

Method: POST

URL: http://localhost:5000/txion

Body (raw, JSON):

JSON

{
    "from": "Alice",
    "to": "Bob",
    "amount": 10
}
Success Response: Transaction submission successful

GET /mine
Tells the node to mine a new block. This will:

Run the Proof-of-Work algorithm (may take a few seconds).

Bundle all transactions from the pool.

Add a reward transaction for the miner.

Add the new block to its chain.

Method: GET

URL: http://localhost:5000/mine

Success Response: A JSON object of the newly mined block.

GET /blocks
Retrieves this node's entire blockchain.

Method: GET

URL: http://localhost:5000/blocks

Success Response: A JSON array of all blocks in the chain.

GET /consensus
Tells the node to run the consensus algorithm: query all peers and replace its chain with the longest valid chain found.

Method: GET

URL: http://localhost:5000/consensus

Success Response:

Consensus run: Chain was replaced... (if a longer valid chain was found)

Consensus run: Our chain remains authoritative. (if no longer valid chain was found)

Running a 2-Node Decentralized Network
This script is designed to be run as two separate processes to simulate a network.

Open Terminal 1 (Node 1): This node will run on port 5000 and will know about Node 2 (at 5001).

Bash

python snakecoin.py 5000
(Server starts on port 5000...)

Open Terminal 2 (Node 2): This node will run on port 5001 and will know about Node 1 (at 5000).

Bash

python snakecoin.py 5001
(Server starts on port 5001...)

Test Scenario: Resolving a Conflict
Now you have two independent nodes. Let's create a conflict and resolve it.

Check Chains (Start):

GET http://localhost:5000/blocks (has 1 block: Genesis)

GET http://localhost:5001/blocks (has 1 block: Genesis)

Mine on Node 1 only:

Send a GET request to http://localhost:5000/mine.

Node 1 now has 2 blocks.

Check for Conflict:

GET http://localhost:5000/blocks (Chain length: 2)

GET http://localhost:5001/blocks (Chain length: 1)

The network is out of sync! Node 2 does not know about the new block.

Run Consensus on Node 2:

Tell Node 2 to check its peers by sending a GET request to http://localhost:5001/consensus.

You will get the response: Consensus run: Chain was replaced...

Check Chains (Final):

GET http://localhost:5001/blocks

Success! Node 2's chain now has 2 blocks. It downloaded the valid chain from Node 1 and adopted it as its own.
