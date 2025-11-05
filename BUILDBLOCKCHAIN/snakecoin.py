import hashlib as hasher
import datetime as date
import json
import requests
from flask import Flask, request
import sys

# =============================================================================
# ## 1. 블록체인 기본 설정
# =============================================================================

# 작업증명(PoW) 난이도. 숫자가 높을수록 채굴이 오래 걸립니다.
# (테스트를 위해 2~4 정도로 낮게 설정하세요.)
DIFFICULTY = 4 

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data # data는 이제 {transactions: [...], nonce: ...} 형태
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """
        블록의 모든 데이터를 기반으로 해시를 계산합니다.
        (Nonce 값도 해시 계산에 포함됩니다)
        """
        sha = hasher.sha256()
        
        # Nonce를 포함한 모든 데이터를 문자열로 결합 후 인코딩
        block_string = (str(self.index) + 
                        str(self.timestamp) + 
                        str(self.data) +  # data 딕셔너리 자체를 문자열로
                        str(self.previous_hash))
        
        sha.update(block_string.encode('utf-8'))
        return sha.hexdigest()


# =============================================================================
# ## 2. 작업증명(PoW) 및 블록 생성 (보안 강화)
# =============================================================================

def proof_of_work(last_block_hash, transactions):
    """
    비트코인과 유사한 작업증명(PoW)
    'DIFFICULTY' 값 만큼의 0으로 시작하는 해시를 찾는 Nonce를 발견할 때까지 무한 반복합니다.
    
    Args:
        last_block_hash (str): 이전 블록의 해시
        transactions (list): 현재 블록에 담을 거래 내역

    Returns:
        (int, str): (찾아낸 Nonce 값, 조건을 만족하는 해시 값)
    """
    nonce = 0
    target = '0' * DIFFICULTY
    
    while True:
        # 1. Nonce와 데이터를 결합하여 추측(guess) 문자열 생성
        data_to_hash = (str(last_block_hash) + 
                        str(transactions) + 
                        str(nonce))
        
        # 2. 해시 계산
        guess_hash = hasher.sha256(data_to_hash.encode('utf-8')).hexdigest()
        
        # 3. 목표(target)와 일치하는지 확인
        if guess_hash.startswith(target):
            # print(f"PoW Found! Nonce: {nonce}, Hash: {guess_hash}") # (디버깅용)
            return nonce, guess_hash # 정답을 찾으면 Nonce와 해시 반환
        
        # 4. 정답이 아니면 Nonce를 1 증가시키고 다시 시도
        nonce += 1


def create_genesis_block():
    """
    첫 번째 제네시스 블록을 생성합니다.
    """
    genesis_data = {
        "transactions": [],
        "nonce": 0 # 제네시스 블록은 PoW가 필요 없으므로 0
    }
    genesis_block = Block(0, date.datetime.now(), genesis_data, "0")
    
    # 제네시스 블록의 해시가 난이도 조건을 만족하도록 수동 조정 (필요시)
    # (간단한 구현을 위해 여기서는 그냥 진행)
    return genesis_block

# =============================================================================
# ## 3. 체인 유효성 검증 (보안 강화)
# =============================================================================

def is_chain_valid(chain):
    """
    전달받은 블록체인이 유효한지 검증합니다.
    1. 각 블록의 'previous_hash'가 이전 블록의 'hash'와 일치하는가?
    2. 각 블록의 해시가 'DIFFICULTY' 조건을 만족(PoW)하는가?
    """
    
    # 1. 제네시스 블록 검증 (간단히 통과)
    if not chain:
        return False
    
    last_block = chain[0]
    current_index = 1
    
    target = '0' * DIFFICULTY

    while current_index < len(chain):
        block = chain[current_index]
        
        # (검증 1) 이전 해시 연결 검증
        if block.previous_hash != last_block.hash:
            print(f"Validation Error: Block {current_index} previous_hash mismatch.")
            return False
        
        # (검증 2) 작업증명(PoW) 검증
        # 블록에 저장된 Nonce와 데이터로 해시를 다시 계산해봄
        data_to_hash = (str(last_block.hash) + 
                        str(block.data['transactions']) + 
                        str(block.data['nonce']))
        
        recalculated_hash = hasher.sha256(data_to_hash.encode('utf-8')).hexdigest()
        
        if not recalculated_hash.startswith(target):
            print(f"Validation Error: Block {current_index} PoW is invalid.")
            return False
            
        # (검증 3) 블록 자체의 해시 무결성 검증 (데이터가 중간에 바뀌었는지)
        # (참고: 이 예제에서는 calculate_hash가 nonce를 포함하지 않아 생략,
        #  실제로는 block.hash == block.calculate_hash() 검증이 필요)

        last_block = block
        current_index += 1
        
    return True # 모든 검증 통과

# =============================================================================
# ## 4. Flask 서버 및 API 설정
# =============================================================================

node = Flask(__name__)

# 채굴자 보상 주소
miner_address = "q3nf394hjg-random-miner-address-34nf3i4nflkn3oi"
# 이 노드에 연결된 다른 노드들
peer_nodes = []
# 이 노드의 임시 거래 내역 (Mempool)
this_nodes_transactions = []
# 블록체인 (리스트)
blockchain = [create_genesis_block()]


@node.route('/txion', methods=['POST'])
def transaction():
    """
    새로운 거래를 POST로 받아 Mempool에 추가
    """
    if request.method == 'POST':
        new_txion = request.get_json()
        this_nodes_transactions.append(new_txion)
        
        print(f"New transaction added: {new_txion}")
        return "Transaction submission successful\n", 201

@node.route('/mine', methods=['GET'])
def mine():
    """
    '/mine' 요청 시, Mempool의 거래내역으로 새 블록을 채굴 (PoW 수행)
    """
    global this_nodes_transactions
    
    # 1. 마지막 블록 정보 가져오기
    last_block = blockchain[-1]
    last_hash = last_block.hash
    
    # 2. 채굴 보상 트랜잭션 추가
    reward_tx = { "from": "network", "to": miner_address, "amount": 1 }
    # (중요) Mempool의 복사본을 만들어 보상 트랜잭션을 추가
    transactions_for_new_block = list(this_nodes_transactions)
    transactions_for_new_block.append(reward_tx)
    
    # 3. 작업증명(PoW) 수행
    # (여기서 서버가 잠시 멈춥니다. DIFFICULTY가 높으면 몇 초~몇 분)
    print("Mining new block...")
    nonce, new_hash = proof_of_work(last_hash, transactions_for_new_block)
    print(f"Mining complete. Found Nonce: {nonce}")

    # 4. 새 블록 데이터 구성
    new_block_data = {
        "transactions": transactions_for_new_block,
        "nonce": nonce
    }
    
    # 5. 새 블록 생성 및 체인에 추가
    new_block = Block(
        index=last_block.index + 1,
        timestamp=date.datetime.now(),
        data=new_block_data,
        previous_hash=last_hash
    )
    # (참고: 실제로는 new_hash와 new_block.hash가 일치하는지 한번 더 검증해야 함)
    blockchain.append(new_block)
    
    # 6. Mempool 비우기
    this_nodes_transactions = []
    
    # 7. 클라이언트에 결과 반환
    return json.dumps({
        "index": new_block.index,
        "timestamp": str(new_block.timestamp),
        "data": new_block.data,
        "hash": new_block.hash
    }), 200

@node.route('/blocks', methods=['GET'])
def get_blocks():
    """
    현재 노드의 전체 블록체인을 JSON으로 반환
    """
    # Block 객체를 JSON으로 변환하기 위해 딕셔너리로 변환
    chain_to_send = []
    for block in blockchain:
        chain_to_send.append({
            "index": block.index,
            "timestamp": str(block.timestamp),
            "data": block.data,
            "hash": block.hash,
            "previous_hash": block.previous_hash
        })
    return json.dumps(chain_to_send), 200

@node.route('/consensus', methods=['GET'])
def run_consensus():
    """
    합의 알고리즘 실행 (보안 강화)
    "가장 길고, 유효한(Valid) 체인"을 선택
    """
    global blockchain
    
    other_chains = find_new_chains() # 다른 노드들의 체인 가져오기
    
    current_len = len(blockchain)
    longest_chain = list(blockchain) # 일단 내 체인을 가장 긴 체인으로
    chain_replaced = False

    for chain_data in other_chains:
        # JSON 딕셔너리 리스트를 Block 객체 리스트로 변환
        chain = [Block(b['index'], b['timestamp'], b['data'], b['previous_hash']) for b in chain_data]
        
        # (검증 1) 내 체인보다 긴가?
        if len(chain) > current_len:
            # (검증 2) 유효한 체인인가? (PoW, 해시 연결)
            if is_chain_valid(chain):
                current_len = len(chain)
                longest_chain = chain
                chain_replaced = True
            else:
                print(f"Received chain from peer is longer but INVALID.")
    
    if chain_replaced:
        blockchain = longest_chain # 유효하고 가장 긴 체인으로 교체
        return "Consensus run: Chain was replaced with the longest valid chain.\n", 200
    else:
        return "Consensus run: Our chain remains authoritative.\n", 200

def find_new_chains():
    """
    'peer_nodes' 목록의 모든 노드로부터 '/blocks'를 호출해 체인을 가져옴
    """
    other_chains = []
    for node_url in peer_nodes:
        try:
            response = requests.get(node_url + "/blocks")
            if response.status_code == 200:
                chain_data = response.json()
                other_chains.append(chain_data)
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to node {node_url}: {e}")
    return other_chains


# =============================================================================
# ## 5. 서버 실행
# =============================================================================

if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 5000
    
    if port == 5000:
        peer_nodes.append('http://127.0.0.1:5001')
    elif port == 5001:
        peer_nodes.append('http://127.0.0.1:5000')
    
    print(f"Starting SnakeCoin node on port {port}")
    print(f"PoW Difficulty set to: {DIFFICULTY}")
    print(f"Peer nodes: {peer_nodes}")
    
    node.run(host='127.0.0.1', port=port)