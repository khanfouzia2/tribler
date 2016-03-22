import random

from hashlib import sha256

from Tribler.dispersy.crypto import ECCrypto
from Tribler.community.multichain.block import MultiChainBlock, GENESIS_ID, EMPTY_SIG, GENESIS_SEQ
from Tribler.Test.test_multichain_utilities import MultiChainTestCase, TestBlock


class TestBlocks(MultiChainTestCase):
    def __init__(self, *args, **kwargs):
        super(TestBlocks, self).__init__(*args, **kwargs)

    def test_hash(self):
        block = MultiChainBlock()
        self.assertEqual(block.hash, 'r\x90\x9fV2\xcb\x9bi\xdd\x888\x11\x9eK\xf6.\xa2\x8c{\xc1\xb5|4w\xd5\xf6\xf0\xfcS'
                                     '\x16<\xb3')

    def test_sign(self):
        crypto = ECCrypto()
        block = TestBlock()
        self.assertTrue(crypto.is_valid_signature(block.key, block.pack(signature=False), block.signature))

    def test_create_genesis(self):
        key = ECCrypto().generate_key(u"curve25519")
        db = self.MockDatabase()
        block = MultiChainBlock.create(db, key.pub().key_to_bin(), link=None)
        self.assertEqual(block.previous_hash, GENESIS_ID)
        self.assertEqual(block.sequence_number, GENESIS_SEQ)
        self.assertEqual(block.public_key, key.pub().key_to_bin())
        self.assertEqual(block.signature, EMPTY_SIG)

    def test_create_next(self):
        db = self.MockDatabase()
        prev = TestBlock()
        prev.sequence_number = GENESIS_SEQ
        db.add_block(prev)
        block = MultiChainBlock.create(db, prev.public_key, link=None)
        self.assertEqual(block.previous_hash, prev.hash)
        self.assertEqual(block.sequence_number, 2)
        self.assertEqual(block.public_key, prev.public_key)

    def test_create_link_genesis(self):
        key = ECCrypto().generate_key(u"curve25519")
        db = self.MockDatabase()
        link = TestBlock()
        db.add_block(link)
        block = MultiChainBlock.create(db, key.pub().key_to_bin(), link=link)
        self.assertEqual(block.previous_hash, GENESIS_ID)
        self.assertEqual(block.sequence_number, GENESIS_SEQ)
        self.assertEqual(block.public_key, key.pub().key_to_bin())
        self.assertEqual(block.link_public_key, link.public_key)
        self.assertEqual(block.link_sequence_number, link.sequence_number)

    def test_create_link_next(self):
        db = self.MockDatabase()
        prev = TestBlock()
        prev.sequence_number = GENESIS_SEQ
        db.add_block(prev)
        link = TestBlock()
        db.add_block(link)
        block = MultiChainBlock.create(db, prev.public_key, link=link)
        self.assertEqual(block.previous_hash, prev.hash)
        self.assertEqual(block.sequence_number, 2)
        self.assertEqual(block.public_key, prev.public_key)
        self.assertEqual(block.link_public_key, link.public_key)
        self.assertEqual(block.link_sequence_number, link.sequence_number)

    def test_pack(self):
        block = MultiChainBlock()
        block.up = 1399791724
        block.down = 1869506336
        block.total_up = 7020658959671910766
        block.total_down = 7742567808708517985
        block.public_key = 'll the fish, so sad that it should come to this. We tried to warn you all '
        block.sequence_number = 1651864608
        block.link_public_key = 'oh dear! You may not share our intellect, which might explain your disresp'
        block.link_sequence_number = 1701016620
        block.previous_hash = ' for all the natural wonders tha'
        block.signature = 't grow around you. So long, so long and thanks for all the fish!'
        self.assertEqual(block.pack(), 'So long and thanks for all the fish, so sad that it should come to this. We '
                                       'tried to warn you all but oh dear! You may not share our intellect, which '
                                       'might explain your disrespect, for all the natural wonders that grow around '
                                       'you. So long, so long and thanks for all the fish!')

    def test_unpack(self):
        block = MultiChainBlock.unpack('So long and thanks for all the fish, so sad that it should come to this. We '
                                       'tried to warn you all but oh dear! You may not share our intellect, which '
                                       'might explain your disrespect, for all the natural wonders that grow around '
                                       'you. So long, so long and thanks for all the fish!')
        self.assertEqual(block.up, 1399791724)
        self.assertEqual(block.down, 1869506336)
        self.assertEqual(block.total_up, 7020658959671910766)
        self.assertEqual(block.total_down, 7742567808708517985)
        self.assertEqual(block.public_key, 'll the fish, so sad that it should come to this. We tried to warn you all ')
        self.assertEqual(block.sequence_number, 1651864608)
        self.assertEqual(block.link_public_key,
                         'oh dear! You may not share our intellect, which might explain your disresp')
        self.assertEqual(block.link_sequence_number, 1701016620)
        self.assertEqual(block.previous_hash, ' for all the natural wonders tha')
        self.assertEqual(block.signature, 't grow around you. So long, so long and thanks for all the fish!')

    def test_validate_existing(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block2)
        db.add_block(block3)
        # Act
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('valid', []))

    def test_validate_non_existing(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block3)
        # Act
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('valid', []))

    def test_validate_no_info(self):
        # Arrange
        db = self.MockDatabase()
        (_, _, _, block4) = self.setup_validate()
        db.add_block(block4)
        # Act
        result = block4.validate(db)
        # Assert
        self.assertEqual(result, ('no-info', ['No blocks are known for this member before or after the queried '
                                              'sequence number']))

    def test_validate_partial_prev(self):
        # Arrange
        db = self.MockDatabase()
        (_, block2, block3, _) = self.setup_validate()
        db.add_block(block2)
        db.add_block(block3)
        # Act
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('partial-prev', []))

    def test_validate_partial_next(self):
        # Arrange
        db = self.MockDatabase()
        (_, block2, block3, _) = self.setup_validate()
        db.add_block(block2)
        db.add_block(block3)
        # Act
        result = block3.validate(db)
        # Assert
        self.assertEqual(result, ('partial-next', []))

    def test_validate_partial(self):
        # Arrange
        db = self.MockDatabase()
        (block1, _, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block3)
        # Act
        result = block3.validate(db)
        # Assert
        self.assertEqual(result, ('partial', []))

    def test_invalid_existing_up(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block2)
        db.add_block(block3)
        # Act
        block2.up += 10
        db.sign_and_propagate()
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Total up is lower than expected compared to the preceding block']))

    def test_invalid_existing_down(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block2)
        db.add_block(block3)
        # Act
        block2.down += 10
        db.sign_and_propagate()
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Total down is lower than expected compared to the preceding block']))

    def test_invalid_existing_total_up(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block2)
        db.add_block(block3)
        # Act
        block2.total_up += 10
        db.sign_and_propagate()
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Total up is higher than expected compared to the next block']))

    def test_invalid_existing_total_down(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block2)
        db.add_block(block3)
        # Act
        block2.total_down += 10
        db.sign_and_propagate()
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Total down is higher than expected compared to the next block']))

    def test_invalid_existing_hash(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block2)
        db.add_block(block3)
        # Act
        block2.previous_hash = sha256(str(random.randint(0, 100000))).digest()
        block2.sign(block2.key)
        block3.previous_hash = block2.hash
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Previous hash is not equal to the hash id of the previous block']))

    def test_invalid_seq_not_genesis(self):
        # Arrange
        db = self.MockDatabase()
        (block1, _, _, _) = self.setup_validate()
        # Act
        block1.previous_hash = sha256(str(random.randint(0, 100000))).digest()
        block1.sign(block1.key)
        result = block1.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Sequence number implies previous hash should be Genesis ID']))

    def test_invalid_seq_genesis(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block3)
        # Act
        block2.previous_hash = GENESIS_ID
        block2.sign(block2.key)
        block3.previous_hash = block2.hash
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', [
            'Sequence number implies previous hash should not be Genesis ID',
            'Genesis block invalid total_up and/or up',
            'Genesis block invalid total_down and/or down',
            'Previous hash is not equal to the hash id of the previous block']))

    def test_invalid_genesis(self):
        # Arrange
        db = self.MockDatabase()
        (block1, _, _, _) = self.setup_validate()
        # Act
        block1.up += 10
        block1.down += 10
        block1.sign(block1.key)
        result = block1.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', [
            'Sequence number implies previous hash should be Genesis ID',
            'Genesis block invalid total_up and/or up',
            'Genesis block invalid total_down and/or down']))

    def test_invalid_up(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block3)
        # Act
        block2.up += 10
        block2.sign(block2.key)
        block3.previous_hash = block2.hash
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Total up is lower than expected compared to the preceding block']))

    def test_invalid_down(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block3)
        # Act
        block2.down += 10
        block2.sign(block2.key)
        block3.previous_hash = block2.hash
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Total down is lower than expected compared to the preceding block']))

    def test_invalid_total_up(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block3)
        # Act
        block2.total_up += 10
        block2.sign(block2.key)
        block3.previous_hash = block2.hash
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Total up is higher than expected compared to the next block']))

    def test_invalid_total_down(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block3)
        # Act
        block2.total_down += 10
        block2.sign(block2.key)
        block3.previous_hash = block2.hash
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Total down is higher than expected compared to the next block']))

    def test_invalid_hash(self):
        # Arrange
        db = self.MockDatabase()
        (block1, block2, block3, _) = self.setup_validate()
        db.add_block(block1)
        db.add_block(block3)
        # Act
        block2.previous_hash = sha256(str(random.randint(0, 100000))).digest()
        block2.sign(block2.key)
        block3.previous_hash = block2.hash
        result = block2.validate(db)
        # Assert
        self.assertEqual(result, ('invalid', ['Previous hash is not equal to the hash id of the previous block']))

    def setup_validate(self):
        block1 = TestBlock()
        block1.sequence_number = GENESIS_SEQ
        block1.previous_hash_requester = GENESIS_ID
        block1.total_up = block1.up
        block1.total_down = block1.down
        block2 = TestBlock(previous=block1)
        block3 = TestBlock(previous=block2)
        block4 = TestBlock()
        return block1, block2, block3, block4

    class MockDatabase(object):
        def __init__(self, *args, **kwargs):
            super(TestBlocks.MockDatabase, self).__init__(*args, **kwargs)
            self.data = dict()

        def sign_and_propagate(self):
            for pk in self.data.keys():
                for i in range(0, len(self.data[pk])):
                    if i > 0:
                        self.data[pk][i].previous_hash = self.data[pk][i-1].hash
                    self.data[pk][i].sign(self.data[pk][i].key)

        def add_block(self, block):
            if self.data.get(block.public_key) is None:
                self.data[block.public_key] = []
            self.data[block.public_key].append(block)
            self.data[block.public_key].sort(key=lambda b: b.sequence_number)

        def contains(self, pk, seq):
            return self.get(pk, seq) is not None

        def get(self, pk, seq):
            if self.data.get(pk) is None:
                return None
            item = [i for i in self.data[pk] if i.sequence_number == seq]
            return item[0] if item else None

        def get_linked(self, blk):
            if self.data.get(blk.link_public_key) is None:
                return None
            item = [i for i in self.data[blk.link_public_key] if
                    i.sequence_number == blk.link_sequence_number or i.link_sequence_number == blk.sequence_number]
            return item[0] if item else None

        def get_latest(self, pk):
            return self.data[pk][-1] if self.data.get(pk) else None

        def get_blocks_since(self, pk, seq, limit=100):
            if self.data.get(pk) is None:
                return []
            return [i for i in self.data[pk] if i.sequence_number >= seq][:limit]

        def get_blocks_until(self, pk, seq, limit=100):
            if self.data.get(pk) is None:
                return []
            return [i for i in self.data[pk] if i.sequence_number <= seq][::-1][:limit]   # TODO: possible in one slice?
