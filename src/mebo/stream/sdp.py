"""Deal with SDP body from the RTSP session creation"""

class Media:
    """A media stream"""

    def __init__(self, name, port, profile, payload_type, **kwargs):
        self.name = name
        self.port = port
        self.profile = profile
        self.payload_type = payload_type
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        profile = self.profile.replace('/', '.')
        return '_'.join([self.name, profile, self.payload_type])


class SDP:
    """
    This class represents and SDP Payload.

    Example sdp:
    v=0
    o=- 1 1 IN IP4 127.0.0.1
    s=Test
    a=type:broadcast
    t=0 0
    c=IN IP4 0.0.0.0
    m=video 0 RTP/AVP 96
    a=rtpmap:96 H264/90001
    a=fmtp:96 packetization-mode=1; profile-level-id=4d0029;; sprop-parameter-sets=,
    a=control:track0
    m=audio 0 RTP/AVP 8
    a=control:track1
    """

    @staticmethod
    def parse_attribute(description):
        attrname, value = description.split(':')
        return attrname, value

    def __init__(self, raw):
        self.media = []
        self._raw = raw
        self._lines = self._raw.splitlines()

        new_media = None
        body_lines = self._lines
        body_lines.reverse()
        while body_lines:
            line = body_lines.pop()
            sdp_code, _, description = line.partition('=')
            if sdp_code == 'v':
                self.version = int(description.strip())
            elif sdp_code == 'o':
                self.originator = description
            elif sdp_code == 'a':
                attribute, value = SDP.parse_attribute(description)
                if new_media is None:
                    setattr(self, attribute, value)
                else:
                    setattr(new_media, attribute, value)
            elif sdp_code == 't':
                self.time = tuple(map(int, description.split()))
            elif sdp_code == 's':
                self.name = description.strip()
            elif sdp_code == 'c':
                self.host_info = description
            elif sdp_code == 'm':
                if new_media is not None:
                    self.media.append(new_media)
                new_media = Media(*description.split())
        if new_media:
            self.media.append(new_media)

    def __iter__(self):
        return (m for m in self.media)
