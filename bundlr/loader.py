from ar import DataItem, ANS104BundleHeader, ANS104DataItemHeader, logger, Transaction
from ar.utils import create_tag, normalize_tag, get_tags

import threading

class Loader:
    def __init__(self, node, gateway, peer, wallet):
        self.node = node
        self.gateway = gateway
        self.peer = peer
        self.wallet = wallet

    def __getattr__(self, attr):
        return getattr(self.peer if '2' in attr or 'sync_' in attr else self.gateway, attr)

    def send(self, data, tags):
        di = DataItem(data = data)
        if type(tags) is dict:
            di.header.tags = [create_tag(name, value, 2) for name, value in tags.items()]
        else:
            di.header.tags = [normalize_tag(tag) for tag in tags]
        di.sign(self.wallet.rsa)
        result = self.node.send_tx(di.tobytes())
        logger.info(result)
        return result['id']

    # this applies to general bundles and could be part of an ans104-associated base class
    def data(self, txid, bundleid = None, blockid = None):
        if bundleid is not None:
            tags = self.tx_tags(bundleid)
            stream = self.stream(bundleid)
            header = ANS104BundleHeader.from_tags_stream(tags, stream)
            offset, end = header.get_range(txid)
            stream.seek(offset)
            dataitem = DataItem.fromstream(stream, length = end - offset)
            data = dataitem.data
        else:
            data = self.data(txid)
        logger.warning(f'{txid} was not verified') # check the hash tree
        return data
    FULL_BLOCK_REQ = b'\xff' * 125
    def full_block(self, block):
        # 2022-06-01: i started implementing this to quickly get validatable tags, but graphql doesn't return a data root, so isn't a quick way to get validatable txs if the peer doesn't have them cached.
        raise NotImplementedError()
        if type(block) is int:
            block = self.peer.block2_height(block, self.FULL_BLOCK_REQ)
        else:
            block = self.peer.block2_hash(block, self.FULL_BLOCK_REQ)
        extra_txs = [txid for txid in block.txs if type(txid) is str]
        #result = self.graphql('''query {
        #    transactions(ids:''' + json.dumps(extra_txs) + ''') {
        #        edges { node {
        #            id anchor signature recipient owner fee quantity
        #            data { size }
        #        } }
        #    }
        #}''')
        print(f'{block.indep_hash} was not verified')
        
    def tags(self, txid, bundleid = None, blockid = None):
        if bundleid is not None:
            tags = self.tx_tags(bundleid)
            stream = self.stream(bundleid)
            if b'json' in get_tags(tags, b'Bundle-Format'):
                bundle = Bundle.from_tags_stream(tags, stream)
                tags = None
                for dataitem in bundle.dataitems:
                    if dataitem.id == txid:
                        tags = dataitem.tags
                        break
            else:
                header = ANS104BundleHeader.from_tags_stream(tags, stream)
                offset = header.get_offset(txid)
                stream.seek(offset)
                dataitem = ANS104DataItemHeader.fromstream(stream)
                tags = dataitem.tags
        else:
            tags = self.tx_tags(txid)
            #tags = Transaction.frombytes(self.tx2(txid)).tags
        logger.warning(f'{txid} was not verified') # check the hash tree
        return tags



