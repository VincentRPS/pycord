"""
The MIT License (MIT)

Copyright (c) 2015-2021 Rapptz & (c) 2021-present Pycord-Development

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import logging
import os
import struct
import sys
import threading
import time

from .errors import SinkException

_log = logging.getLogger(__name__)

__all__ = (
    "Filters",
    "Sink",
    "AudioData",
    "RawData",
)


if sys.platform != "win32":
    CREATE_NO_WINDOW = 0
else:
    CREATE_NO_WINDOW = 0x08000000


default_filters = {
    "time": 0,
    "users": [],
    "max_size": 0,
}


class Filters:
    """Filters for sink

    .. versionadded:: 2.1

    Parameters
    ----------
    container
        Container of all Filters.

    """

    def __init__(self, **kwargs):
        self.filtered_users = kwargs.get("users", default_filters["users"])
        self.seconds = kwargs.get("time", default_filters["time"])
        self.max_size = kwargs.get("max_size", default_filters["max_size"])
        self.finished = False

    @staticmethod
    def container(func):  # Contains all filters
        def _filter(self, data, user):
            if not self.filtered_users or user in self.filtered_users:
                return func(self, data, user)

        return _filter

    def init(self):
        if self.seconds != 0:
            thread = threading.Thread(target=self.wait_and_stop)
            thread.start()

    def wait_and_stop(self):
        time.sleep(self.seconds)
        if self.finished:
            return
        self.vc.stop_listening()


class RawData:
    """Handles raw data from Discord so that it can be decrypted and decoded to be used.

    .. versionadded:: 2.1

    """

    def __init__(self, data, client):
        self.data = bytearray(data)
        self.client = client

        self.header = data[:12]
        self.data = self.data[12:]

        unpacker = struct.Struct(">xxHII")
        self.sequence, self.timestamp, self.ssrc = unpacker.unpack_from(self.header)
        self.decrypted_data = getattr(self.client, "_decrypt_" + self.client.mode)(
            self.header, self.data
        )
        self.decoded_data = None

        self.user_id = None


class AudioData:
    """Handles data that's been completely decrypted and decoded and is ready to be saved to file.

    .. versionadded:: 2.1

    Raises
    ------
    ClientException
        The AudioData is already finished writing,
        The AudioData is still writing
    """

    def __init__(self, file):
        self.file = open(file, "ab")
        self.dir_path = os.path.split(file)[0]

        self.finished = False

    def write(self, data):
        if self.finished:
            raise SinkException("The AudioData is already finished writing.")
        try:
            self.file.write(data)
        except ValueError:
            pass

    def cleanup(self):
        if self.finished:
            raise SinkException("The AudioData is already finished writing.")
        self.file.close()
        self.file = os.path.join(self.dir_path, self.file.name)
        self.finished = True

    def on_format(self, encoding):
        if not self.finished:
            raise SinkException("The AudioData is still writing.")
        name = os.path.split(self.file)[1]
        name = name.split(".")[0] + f".{encoding}"
        self.file = os.path.join(self.dir_path, name)


class Sink(Filters):
    """A Sink "stores" all the audio data.

    Can be subclassed for extra customizablilty,

    .. warning::

        It is although recommended you use,
        the officially provided sink classes
        like :class:`~discord.sinks.WaveSink`

    just replace the following like so: ::

        vc.start_recording(
            MySubClassedSink(),
            finished_callback,
            ctx.channel,
        )

    .. versionadded:: 2.1

    Parameters
    ----------
    output_path: :class:`string`
        A path to where the audio files should be output.

    Raises
    ------
    ClientException
        An invalid encoding type was specified.
        Audio may only be formatted after recording is finished.
    """

    def __init__(self, *, output_path="", filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)
        self.file_path = output_path
        self.vc = None
        self.audio_data = {}

    def init(self, vc):  # called under listen
        self.vc = vc
        super().init()

    @Filters.container
    def write(self, data, user):
        if user not in self.audio_data:
            ssrc = self.vc.get_ssrc(user)
            file = os.path.join(self.file_path, f"{ssrc}.pcm")
            self.audio_data.update({user: AudioData(file)})

        file = self.audio_data[user]
        file.write(data)

    def cleanup(self):
        self.finished = True
        for file in self.audio_data.values():
            file.cleanup()
            self.format_audio(file)