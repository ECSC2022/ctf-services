# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import BytesIO, KaitaiStream, KaitaiStruct

if getattr(kaitaistruct, "API_VERSION", (0, 9)) < (0, 9):
    raise Exception(
        "Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s"
        % (kaitaistruct.__version__)
    )


class Vgm(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = Vgm.Header(self._io, self, self._root)

    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.magic = self._io.read_bytes(4)
            if not self.magic == b"\x56\x67\x6D\x20":
                raise kaitaistruct.ValidationNotEqualError(
                    b"\x56\x67\x6D\x20", self.magic, self._io, "/types/header/seq/0"
                )
            self.eof_offset = self._io.read_u4le()
            self.version_number = self._io.read_u4le()
            self.sn76489_clock = self._io.read_u4le()
            self.ym2413_clock = self._io.read_u4le()
            self.gd3_offset = self._io.read_u4le()
            self.total_samples = self._io.read_u4le()
            self.loop_offset = self._io.read_u4le()
            self.loop_samples = self._io.read_u4le()
            self.rate = self._io.read_u4le()
            self.sn76489_feedback = self._io.read_u2le()
            self.sn76489_shift_register_width = self._io.read_u1()
            self.sn76489_flags = self._io.read_u1()
            self.ym2612_clock = self._io.read_u4le()
            self.ym2151_clock = self._io.read_u4le()
            self.vgm_data_offset = self._io.read_u4le()
            self.sega_pcm_clock = self._io.read_u4le()
            self.sega_pcm_interface_register = self._io.read_u4le()
            self.rf5c68_clock = self._io.read_u4le()
            self.ym2203_clock = self._io.read_u4le()
            self.ym2608_clock = self._io.read_u4le()
            self.ym2610_ym2610b_clock = self._io.read_u4le()
            self.ym3812_clock = self._io.read_u4le()
            self.ym3526_clock = self._io.read_u4le()
            self.y8950_clock = self._io.read_u4le()
            self.ymf262_clock = self._io.read_u4le()
            self.ymf278b_clock = self._io.read_u4le()
            self.ymf271_clock = self._io.read_u4le()
            self.ymz280b_clock = self._io.read_u4le()
            self.rf5c164_clock = self._io.read_u4le()
            self.pwm_clock = self._io.read_u4le()
            self.ay8910_clock = self._io.read_u4le()
            self.ay8910_chip_type = self._io.read_u1()
            self.ay8910_flags = self._io.read_u1()
            self.ym2203_ay8910_flags = self._io.read_u1()
            self.ym2608_ay8910_flags = self._io.read_u1()
            self.volume_modifier = self._io.read_u1()
            self.reserved_1 = self._io.read_u1()
            self.loop_base = self._io.read_u1()
            self.loop_modifier = self._io.read_u1()
            self.gameboy_dmg_clock = self._io.read_u4le()
            self.nes_apu_clock = self._io.read_u4le()
            self.multipcm_clock = self._io.read_u4le()
            self.upd7759_clock = self._io.read_u4le()
            self.okim6258_clock = self._io.read_u4le()
            self.okim6258_flags = self._io.read_u1()
            self.k054539_flags = self._io.read_u1()
            self.c140_chip_type = self._io.read_u1()
            self.reserved = self._io.read_u1()
            self.okim6295_clock = self._io.read_u4le()
            self.k051649_k052539_clock = self._io.read_u4le()
            self.k054539_clock = self._io.read_u4le()
            self.huc6280_clock = self._io.read_u4le()
            self.c140_clock = self._io.read_u4le()
            self.k053260_clock = self._io.read_u4le()
            self.pokey_clock = self._io.read_u4le()
            self.qsound_clock = self._io.read_u4le()
            self.scsp_clock = self._io.read_u4le()
            self.extra_header_offset = self._io.read_u4le()
            self.wonderswan_clock = self._io.read_u4le()
            self.vsu_clock = self._io.read_u4le()
            self.saa1099_clock = self._io.read_u4le()
            self.es5503_clock = self._io.read_u4le()
            self.es5505_es5506_clock = self._io.read_u4le()
            self.es5503_amount_of_output_channels = self._io.read_u1()
            self.es5505_es5506_amount_of_output_channels = self._io.read_u1()
            self.c352_clock_divider = self._io.read_u1()
            self.x1_010_clock = self._io.read_u4le()
            self.c352_clock = self._io.read_u4le()
            self.ga20_clock = self._io.read_u4le()

    class Gd3Tag(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.magic = self._io.read_bytes(4)
            if not self.magic == b"\x47\x64\x33\x20":
                raise kaitaistruct.ValidationNotEqualError(
                    b"\x47\x64\x33\x20", self.magic, self._io, "/types/gd3_tag/seq/0"
                )
            self.version = self._io.read_u4le()
            self.length = self._io.read_u4le()
            self.track = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.track.append(_)
                if _ == 0:
                    break
                i += 1
            self.track_jp = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.track_jp.append(_)
                if _ == 0:
                    break
                i += 1
            self.game = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.game.append(_)
                if _ == 0:
                    break
                i += 1
            self.game_jp = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.game_jp.append(_)
                if _ == 0:
                    break
                i += 1
            self.system = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.system.append(_)
                if _ == 0:
                    break
                i += 1
            self.system_jp = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.system_jp.append(_)
                if _ == 0:
                    break
                i += 1
            self.author = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.author.append(_)
                if _ == 0:
                    break
                i += 1
            self.author_jp = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.author_jp.append(_)
                if _ == 0:
                    break
                i += 1
            self.release_date = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.release_date.append(_)
                if _ == 0:
                    break
                i += 1
            self.converted_by = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.converted_by.append(_)
                if _ == 0:
                    break
                i += 1
            self.notes = []
            i = 0
            while True:
                _ = self._io.read_u2le()
                self.notes.append(_)
                if _ == 0:
                    break
                i += 1

    @property
    def data(self):
        if hasattr(self, "_m_data"):
            return self._m_data

        _pos = self._io.pos()
        self._io.seek((self.header.vgm_data_offset + 52))
        self._m_data = self._io.read_bytes(
            ((self.header.gd3_offset + 20) - (self.header.vgm_data_offset + 52))
        )
        self._io.seek(_pos)
        return getattr(self, "_m_data", None)

    @property
    def gd3(self):
        if hasattr(self, "_m_gd3"):
            return self._m_gd3

        _pos = self._io.pos()
        self._io.seek((self.header.gd3_offset + 20))
        self._raw__m_gd3 = self._io.read_bytes_full()
        _io__raw__m_gd3 = KaitaiStream(BytesIO(self._raw__m_gd3))
        self._m_gd3 = Vgm.Gd3Tag(_io__raw__m_gd3, self, self._root)
        self._io.seek(_pos)
        return getattr(self, "_m_gd3", None)
