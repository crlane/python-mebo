"""
Based on the work here:

    https://gist.github.com/jn0/8b98652f9fb8f8d7afbf4915f63f6726

    http://stackoverflow.com/questions/28022432/receiving-rtp-packets-after-rtsp-setup
    A demo python code that ..

    1) Connects to an IP cam with RTSP
    2) Draws RTP/NAL/H264 packets from the camera
    3) Writes them to a file that can be read with any stock video player (say, mplayer, vlc & other ffmpeg based video-players)

    Done for educative/demonstrative purposes, not for efficiency..!

    written 2015 by Sampsa Riikonen.


Adapted to python3
"""

import struct
import logging

logger = logging.getLogger(__name__)


def get_bits(d, size=32):
    m, M = 0, 2**size - 1
    if not (m <= d <= M):
        raise ValueError(f'{d} must be in the range [{m},{M}]')
    binary = f'{d:0>{size}b}'
    assert len(binary) == size
    return {i: digit for i, digit in enumerate(binary)}


class NALType:

    RESERVED = {0, 30, 31}
    UNIT = set(range(1, 24))

    STAP_A = 24
    STAP_B = 25
    MTAP16 = 26
    MTAP24 = 27
    FU_A = 28
    FU_B = 29

    @classmethod
    def supported(cls):
        return {
            cls.STAP_A,
            cls.FU_A
        }.union(cls.UNIT)

    @classmethod
    def unsupported(cls):
        return {
            cls.STAP_B,
            cls.MTAP16,
            cls.MTAP24,
            cls.FU_B,
        }.union(cls.RESERVED)


class RTPDecodeError(Exception):
    pass


class RTPPacket:

    def __init__(self, packet):
        self.raw = memoryview(packet)
        self.byte_offset = 0
        self.version = 0
        self.padding = 0
        self.contributors = 0
        self.marker = 0
        self.payload_type = 0
        self.sequence_number = 0
        self.timestamp = 0

        # optional extensions
        self.header_id = None
        self.header_length = None
        self.header_contents = None

    @property
    def bytes(self):
        return self.raw.tobytes()

    def parse_header(self):
        # The first 8-bytes represent the RTP header value
        # the header format can be found from:
        # https://en.wikipedia.org/wiki/Real-time_Transport_Protocol
        # https://tools.ietf.org/html/rfc3550#section-5.1
        #
        #     0                   1                   2                   3
        #     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        #     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        #     |V=2|P|X|  CC   |M|     PT      |       sequence number         |
        #     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        #     |                           timestamp                           |
        #     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        #     |           synchronization source (SSRC) identifier            |
        #     +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
        #     |            contributing source (CSRC) identifiers             |
        #     |                             ....                              |
        #     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        #
        #     The first twelve octets (96 bits) are present in every RTP packet, while the
        #     list of CSRC identifiers is present only when inserted by a mixer.
        #     The fields have the following meaning:

        #     Required fields:
        #     version (V): 2 bits
        #     padding (P): 1 bit
        #     extension (X): 1 bit
        #     CSRC count (CC): 4 bits
        #     marker (M): 1 bit
        #     payload type (PT): 7 bits
        #     sequence number (M): 16 bits
        #     timestamp: 32 bits
        #     SSRC: 32 bits

        # the first 12 bytes we'll pack into three, 32-bit unsigned ints
        # then use bit shifting/twiddling to get the parts we want
        # consumes the first 12 bytes or 96 bits
        standard_header = self.raw[:12]
        self.byte_offset += 12

        meta, self.timestamp, self.ssrc = struct.unpack('!III', standard_header)
        # first 16 bits of the first uint32
        first_16 = meta >> 16
        self.sequence_number = meta & ((1 << 16) - 1)  # last 16 bits of the first uint32
        logger.debug('Sequence number: %d, Timestamp: %d, SSRC: %x', self.sequence_number, self.timestamp, self.ssrc)

        self.version = first_16 >> 14  # first two bits, 23 == 0x17 == 3 << 14 ==
        if self.version != 2:
            raise RTPDecodeError(f'Unknown version {self.version} error!')
        self.padding = (first_16 >> 13) & 1  # third bit
        self.extension = (first_16 >> 12) & 1  # fourth bit
        self.contributors = first_16 & ((1 << 4) - 1)   # bits 5-8
        self.marker = first_16 & (1 << 7)  # bit 9

        self.payload_type = first_16 & ((1 << 7) - 1)  # last 7 bits of first two bytes

        if self.contributors:
            orig_offset = self.byte_offset
            self.byte_offset += (4 * self.contributors)
            struct_mask = ''.join(['!', 'I' * self.contributors])
            self.contributing_sources = struct.unpack(struct_mask, self.raw[orig_offset: self.byte_offset])
            logger.debug("CRSC identifiers: %s", [f'{csrc:x}' for csrc in self.contributing_sources])

        if self.extension:
            # these are unsigned 16-bit integers 'H' in struct unpack land
            orig_offset = self.byte_offset
            self.byte_offset += 2
            self.header_id = struct.unpack('!H', self.raw[orig_offset: self.byte_offset])

            orig_offset = self.byte_offset
            self.byte_offset += 2
            self.header_length = struct.unpack('!H', self.raw[orig_offset: self.byte_offset])
            logger.debug('Extended header id (%d) with length %d', self.header_id, self.header_length)

            orig_offset = self.byte_offset
            self.byte_offset += (4 * self.header_length)
            self.header_contents = self.raw[orig_offset: self.byte_offset]


    def decode(self, media_type):
        self.parse_header()
        if media_type == 'video':
            return self._decode_video()
        elif media_type == 'audio':
            return self._decode_audio()
        else:
            raise ValueError(f'Unknown sdp media type {media_type}')

    def _decode_audio(self, code='g711a'):
        """ Writes out everything after the header """
        return self.raw[self.byte_offset:]

    def _decode_video(self, codec='h264', packetization_mode=1):
        """ This routine takes a UDP packet, i.e. a string of bytes and ..
        (a) strips off the RTP header
        (b) adds NAL "stamps" to the packets, so that they are recognized as NAL's
        (c) Concantenates frames
        (d) Returns a packet that can be written to disk as such and that is recognized by stock media players as h264 stream
        """
        # this is the sequence of four bytes that identifies a NAL packet.. must be in front of every NAL packet.
        startbytes = b'\x00\x00\x00\x01'

        # OK, all of the header has been consumed.
        # now we enter the NAL packet, as described here:
        # https://tools.ietf.org/html/rfc6184#section-1.3
        # Some quotes from that document:
        """
        5.3. NAL Unit Header Usage


        The structure and semantics of the NAL unit header were introduced in
        Section 1.3.  For convenience, the format of the NAL unit header is
        reprinted below:

            +---------------+
            |0|1|2|3|4|5|6|7|
            +-+-+-+-+-+-+-+-+
            |F|NRI|  Type   |
            +---------------+

        This section specifies the semantics of F and NRI according to this
        specification.

        """
        """
        Table 3.  Summary of allowed NAL unit types for each packetization
                      mode (yes  =  allowed, no  =  disallowed, ig  =  ignore)

            Payload Packet    Single NAL    Non-Interleaved    Interleaved
            Type    Type      Unit Mode           Mode             Mode
            -------------------------------------------------------------
            0      reserved      ig               ig               ig
            1-23   NAL unit     yes              yes               no
            24     STAP-A        no              yes               no
            25     STAP-B        no               no              yes
            26     MTAP16        no               no              yes
            27     MTAP24        no               no              yes
            28     FU-A          no              yes              yes
            29     FU-B          no               no              yes
            30-31  reserved      ig               ig               ig
        """
        # This was also very usefull:
        # http://stackoverflow.com/questions/7665217/how-to-process-raw-udp-packets-so-that-they-can-be-decoded-by-a-decoder-filter-i
        # A quote from that:
        """
        First byte:  [ 3 NAL UNIT BITS | 5 FRAGMENT TYPE BITS]
        Second byte: [ START BIT | END BIT | RESERVED BIT | 5 NAL UNIT BITS]
        Other bytes: [... VIDEO FRAGMENT DATA...]
        """

        self.NAL = self.raw[self.byte_offset]
        self.f = (self.NAL & 0x80) >> 7  # bit 1, forbidden bit. Should be 0
        self.nri = (self.NAL & 0x60) >> 5  # bit 2-3, NAL ref IDC
        self.fragment_type = self.NAL & 0x1F  # ((1 << 5) - 1)
        self.nlu0 = self.f | self.nri

        logger.debug('F:%d, NRI:%d, Type:%d', self.f, self.nri, self.fragment_type)
        # logger.debug('NLU: %d', self.nlu0)

        if self.fragment_type in NALType.UNIT:
            # this means we have either an SPS or a PPS packet
            # they have the meta-info about resolution, etc.
            # more reading for example here:
            # http://www.cardinalpeak.com/blog/the-h-264-sequence-parameter-set/
            if self.fragment_type == 1:
                logger.debug('<<<<< NAL unit type (%d), decoding', self.fragment_type)
            if self.fragment_type == 7:
                logger.debug(">>>>> SPS packet")
            else:
                logger.debug(">>>>> PPS packet")
            # .. notice here that we include the NAL starting sequence "startbytes" and the "First byte"
            return startbytes + self.raw[self.byte_offset:]

        else:
            self.byte_offset += 1

        # let's go to "Second byte"
        # ********* WE ARE AT THE "Second byte" ************
        # The "Type" here is most likely 28, i.e. "FU-A"
        second_byte = self.raw[self.byte_offset]
        self.start = (second_byte & 0x80) >> 7  # 128
        self.end = (second_byte & 0x40) >> 6  # 64
        self.reserved = (second_byte & 0x20) >> 5  # 32
        self.nlu1 = second_byte & 0x1F

        if self.start:  # OK, this is a first fragment in a movie frame
            logger.debug('>>>>> first fragment found')
            self.nlu = bytes([self.nlu0 | self.nlu1])  # Create "[3 NAL UNIT BITS | 5 NAL UNIT BITS]"
            # possibly decode bytes as latin-1?
            head = startbytes + self.nlu   # .. add the NAL starting sequence
            self.byte_offset += 1
        else:
            if self.end:
                logger.debug('<<<<< last fragment found')
            else:
                logger.debug('<<<<< intermediate fragment found')
            head = bytes()
            self.byte_offset += 1

        if self.fragment_type not in NALType.supported():
            raise RTPDecodeError(f'Got unsupported NALType {self.fragment_type} for packetization-mode 1')
        elif self.fragment_type == NALType.STAP_A:
            logger.debug('<<<<< STAP_A NALType: (%d), decoding', self.fragment_type)
        elif self.fragment_type == NALType.FU_A:  # This code only handles "Type"  =  28, i.e. "FU-A"
            logger.debug('<<<<< FU_A NALType: (%d), decoding', self.fragment_type)
        return head + self.raw[self.byte_offset:]
