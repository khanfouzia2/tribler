import os
from datetime import datetime

from pony.orm import db_session
from twisted.internet.defer import inlineCallbacks

from Tribler.Core.Modules.MetadataStore.OrmBindings.channel_node import NEW
from Tribler.Core.Modules.MetadataStore.store import MetadataStore
from Tribler.Core.Modules.gigachannel_manager import GigaChannelManager
from Tribler.Core.TorrentDef import TorrentDef
from Tribler.Test.Core.base_test import TriblerCoreTest, MockObject
from Tribler.Test.common import TORRENT_UBUNTU_FILE
from Tribler.pyipv8.ipv8.database import database_blob
from Tribler.pyipv8.ipv8.keyvault.crypto import default_eccrypto


class TestGigaChannelManager(TriblerCoreTest):

    @db_session
    def generate_personal_channel(self):
        chan = self.mock_session.lm.mds.ChannelMetadata.create_channel(title="my test chan", description="test")
        my_dir = os.path.abspath(os.path.join(self.mock_session.lm.mds.channels_dir, chan.dir_name))
        tdef = TorrentDef.load(TORRENT_UBUNTU_FILE)
        chan.add_torrent_to_channel(tdef, None)
        return chan

    @inlineCallbacks
    def setUp(self):
        yield super(TestGigaChannelManager, self).setUp()
        self.torrent_template = {
            "title": "",
            "infohash": "",
            "torrent_date": datetime(1970, 1, 1),
            "tags": "video"
        }
        my_key = default_eccrypto.generate_key(u"curve25519")
        self.mock_session = MockObject()
        self.mock_session.lm = MockObject()
        self.mock_session.lm.mds = MetadataStore(os.path.join(self.session_base_dir, 'test.db'), self.session_base_dir,
                                                 my_key)

        self.chanman = GigaChannelManager(self.mock_session)

    @inlineCallbacks
    def tearDown(self):
        self.mock_session.lm.mds.shutdown()
        yield super(TestGigaChannelManager, self).tearDown()

    @db_session
    def test_update_my_channel(self):
        chan = self.generate_personal_channel()
        chan.commit_channel_torrent()
        self.torrent_added = False

        def mock_add(a, b):
            self.torrent_added = True

        self.mock_session.lm.add = mock_add
        #   self.mock_session.has_download = lambda x: x == str(chan.infohash)

        # Check add personal channel on startup
        self.mock_session.has_download = lambda _: False
        self.chanman.service_channels = lambda: None  # Disable looping call
        self.chanman.start()
        self.chanman.check_channels_updates()
        self.assertTrue(self.torrent_added)
        self.chanman.shutdown()

        # Check skip already added personal channel
        self.mock_session.has_download = lambda x: x == str(chan.infohash)
        self.torrent_added = False
        self.chanman.start()
        self.chanman.check_channels_updates()
        self.assertFalse(self.torrent_added)
        self.chanman.shutdown()

    def test_check_channels_updates(self):
        with db_session:
            chan = self.generate_personal_channel()
            chan.commit_channel_torrent()
            chan.local_version -= 1
            chan2 = self.mock_session.lm.mds.ChannelMetadata(title="bla", public_key=database_blob(str(123)),
                                                             signature=database_blob(str(345)), skip_key_check=True,
                                                             timestamp=123, local_version=123, subscribed=True)
            chan3 = self.mock_session.lm.mds.ChannelMetadata(title="bla", public_key=database_blob(str(124)),
                                                             signature=database_blob(str(346)), skip_key_check=True,
                                                             timestamp=123, local_version=122, subscribed=False)
        self.mock_session.has_download = lambda _: False
        self.torrent_added = 0

        def mock_dl(a):
            self.torrent_added += 1

        self.chanman.download_channel = mock_dl

        self.chanman.check_channels_updates()
        # download_channel should only fire once - for the original subscribed channel
        self.assertEqual(1, self.torrent_added)

    def test_remove_cruft_channels(self):
        with db_session:
            # Our personal chan is created, then updated, so there are 2 files on disk and there are 2 torrents:
            # the old one and the new one
            my_chan = self.generate_personal_channel()
            my_chan.commit_channel_torrent()
            my_chan_old_infohash = my_chan.infohash
            md = self.mock_session.lm.mds.TorrentMetadata.from_dict(dict(self.torrent_template, status=NEW))
            my_chan.commit_channel_torrent()

            # Now we add external channel we are subscribed to.
            chan2 = self.mock_session.lm.mds.ChannelMetadata(title="bla1", infohash=database_blob(str(123)),
                                                             public_key=database_blob(str(123)),
                                                             signature=database_blob(str(345)), skip_key_check=True,
                                                             timestamp=123, local_version=123, subscribed=True)

            # Another external channel, but there is a catch: we recently unsubscribed from it
            chan3 = self.mock_session.lm.mds.ChannelMetadata(title="bla2", infohash=database_blob(str(124)),
                                                             public_key=database_blob(str(124)),
                                                             signature=database_blob(str(346)), skip_key_check=True,
                                                             timestamp=123, local_version=123, subscribed=False)

        class mock_dl(MockObject):
            def __init__(self, infohash, dirname):
                self.infohash = infohash
                self.dirname = dirname

            def get_def(self):
                a = MockObject()
                a.infohash = self.infohash
                a.get_name_utf8 = lambda: self.dirname
                return a

        # Double conversion is required to make sure that buffers signatures are not the same
        mock_dl_list = [
            # Downloads for our personal channel
            mock_dl(database_blob(bytes(my_chan_old_infohash)), my_chan.dir_name),
            mock_dl(database_blob(bytes(my_chan.infohash)), my_chan.dir_name),

            # Downloads for the updated external channel: "old ones" and "recent"
            mock_dl(database_blob(bytes(str(12331244))), chan2.dir_name),
            mock_dl(database_blob(bytes(chan2.infohash)), chan2.dir_name),

            # Downloads for the unsubscribed external channel
            mock_dl(database_blob(bytes(str(1231551))), chan3.dir_name),
            mock_dl(database_blob(bytes(chan3.infohash)), chan3.dir_name),
            # Orphaned download
            mock_dl(database_blob(str(333)), u"blabla")]

        def mock_get_channel_downloads():
            return mock_dl_list

        self.remove_list = []

        def mock_remove_channels_downloads(remove_list):
            self.remove_list = remove_list

        self.chanman.remove_channels_downloads = mock_remove_channels_downloads
        self.mock_session.lm.get_channel_downloads = mock_get_channel_downloads
        self.chanman.remove_cruft_channels()
        # We want to remove torrents for (a) deleted channels and (b) unsubscribed channels
        self.assertItemsEqual(self.remove_list,
                              [(mock_dl_list[0], False),
                               (mock_dl_list[2], False),
                               (mock_dl_list[4], True),
                               (mock_dl_list[5], True),
                               (mock_dl_list[6], True)])
