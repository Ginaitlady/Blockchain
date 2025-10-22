import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # 제네시스 블록 (가장 첫 블록) 생성
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address: str):
        """
        노드 목록에 새 노드를 추가합니다. :param address: 노드의 주소 (예: 'http://192.168.0.5:5000')
        """
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # '192.168.0.5:5000'와 같은 주소를 받아들입니다.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def valid_chain(self, chain: list) -> bool:
        """
        주어진 블록체인이 유효한지 확인합니다. :param chain: 블록체인 :return: True or False
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")

            # 블록의 해시가 올바른지 확인
            if block['previous_hash'] != self.hash(last_block):
                return False

            # 작업 증명이 올바른지 확인
            if not self.valid_proof(last_block['proof'], block['proof'], self.hash(last_block)):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self) -> bool:
        """
        합의 알고리즘입니다. 네트워크에서 가장 긴 체인을 찾아 우리 체인으로 교체하여 충돌을 해결합니다.
        :return: 우리 체인이 교체되었으면 True, 아니면 False
        """
        neighbours = self.nodes
        new_chain = None

        # 우리 체인보다 긴 체인을 찾습니다.
        max_length = len(self.chain)

        # 네트워크의 모든 노드에서 체인을 가져와 확인합니다.
        for node in neighbours:
            try:
                response = requests.get(f'http://{node}/chain')

                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']

                    # 길이가 더 길고, 체인이 유효한지 확인합니다.
                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except requests.exceptions.RequestException as e:
                print(f"Could not connect to node {node}: {e}")
                continue


        # 만약 우리 체인보다 길고 유효한 체인을 찾았다면 교체합니다.
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof: int, previous_hash: str = None) -> dict:
        """
        체인에 새로운 블록을 생성.
        :param proof: 작업 증명 알고리즘으로 얻은 증명 값
        :param previous_hash: 이전 블록의 해시
        :return: 새 블록
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # 현재 거래 목록을 리셋합니다.
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: float) -> int:
        """
        다음 채굴될 블록에 추가될 새로운 거래를 생성.
        :param sender: 보내는 사람의 주소
        :param recipient: 받는 사람의 주소
        :param amount: 금액
        :return: 이 거래가 추가될 블록의 인덱스
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self) -> dict:
        return self.chain[-1]

    @staticmethod
    def hash(block: dict) -> str:
        """
        블록의 SHA-256 해시를 생성.
        :param block: 블록
        :return: 해시 문자열
        """
        # 딕셔너리가 순서대로 정렬되도록 보장해야 합니다. 그렇지 않으면 해시가 일관되지 않습니다.
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block: dict) -> int:
        """
        간단한 작업 증명 알고리즘:
         - 이전 증명(last_proof)과 이전 해시(previous_hash)를 포함하는 해시를 찾습니다.
         - 이 해시는 반드시 앞자리가 0이 4개여야 합니다.
        :param last_block: 마지막 블록
        :return: 증명 값 (정수)
        """
        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int, last_hash: str) -> bool:
        """
        증명이 유효한지 확인합니다: 해시(last_proof, proof, last_hash)가 0으로 시작하는가?
        :param last_proof: 이전 증명
        :param proof: 현재 증명
        :param last_hash: 이전 블록의 해시
        :return: True or False
        """
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# --- API 부분 ---

# Flask 앱 인스턴스화
app = Flask(__name__)

# 이 노드의 전역 고유 주소 생성
node_identifier = str(uuid4()).replace('-', '')

# Blockchain 클래스 인스턴스화
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # 다음 증명을 얻기 위해 작업 증명 알고리즘을 실행합니다.
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # 채굴에 대한 보상을 받아야 합니다.
    # 보낸 사람이 "0"인 것은 이 노드가 새 코인을 채굴했다는 것을 의미합니다.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # 체인에 새 블록을 추가하여 위조합니다.
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # 필요한 필드 (sender, recipient, amount)가 POST된 데이터에 있는지 확인합니다.
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # 새로운 거래를 생성합니다.
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':

    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)