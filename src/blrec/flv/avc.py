from __future__ import annotations
import io
import math
from typing import Final, List, Tuple

import attr
from bitarray import bitarray

from .struct_io import StructReader
from .bits_io import BitsReader
from .utils import OffsetRepositor


__all__ = (
    'AVCDecoderConfigurationRecord',
    'SequenceParameterSet',
    'PictureParameterSet',
    'AVCSequenceHeaderParser',
    'NalUnit',
    'NalUnitParser',
    'SequenceParameterSetData',
    'SequenceParameterSetRBSPParser',
    'extract_resolution',
)


# ISO/IEC 14496-15:2010(E)
# 5.2.4.1.1 Syntax
# 5.2.4.1.2 Semantics

@attr.s(auto_attribs=True, slots=True, frozen=True)
class AVCDecoderConfigurationRecord:
    configuration_Version: int
    avc_profile_indication: int
    profile_compatibility: int
    avc_level_indication: int
    length_size_minus_one: int
    num_of_sequence_parameter_sets: int
    sequence_parameter_sets: List[SequenceParameterSet]
    num_of_picture_parameter_sets: int
    picture_parameter_sets: List[PictureParameterSet]
    # extensions ignored


@attr.s(auto_attribs=True, slots=True, frozen=True)
class SequenceParameterSet:
    sequence_parameter_set_length: int
    sequence_parameter_set_nal_unit: bytes


@attr.s(auto_attribs=True, slots=True, frozen=True)
class PictureParameterSet:
    picture_parameter_set_length: int
    picture_parameter_set_nal_unit: bytes


class AVCSequenceHeaderParser:
    def parse(self, data: bytes) -> AVCDecoderConfigurationRecord:
        reader = StructReader(io.BytesIO(data))

        configuration_Version = reader.read_ui8()
        avc_profile_indication = reader.read_ui8()
        profile_compatibility = reader.read_ui8()
        avc_level_indication = reader.read_ui8()
        length_size_minus_one = reader.read_ui8() & ~0b1111_1100

        num_of_sequence_parameter_sets = reader.read_ui8() & ~0b1110_0000
        sequence_parameter_sets: List[SequenceParameterSet] = []

        for _ in range(num_of_sequence_parameter_sets):
            sequence_parameter_set_length = reader.read_ui16()
            sequence_parameter_set_nal_unit = reader.read(
                sequence_parameter_set_length
            )
            sequence_parameter_sets.append(
                SequenceParameterSet(
                    sequence_parameter_set_length,
                    sequence_parameter_set_nal_unit,
                )
            )

        num_of_picture_parameter_sets = reader.read_ui8()
        picture_parameter_sets: List[PictureParameterSet] = []

        for _ in range(num_of_picture_parameter_sets):
            picture_parameter_set_length = reader.read_ui16()
            picture_parameter_set_nal_unit = reader.read(
                picture_parameter_set_length
            )
            picture_parameter_sets.append(
                PictureParameterSet(
                    picture_parameter_set_length,
                    picture_parameter_set_nal_unit,
                )
            )

        # extensions ignored

        return AVCDecoderConfigurationRecord(
            configuration_Version,
            avc_profile_indication,
            profile_compatibility,
            avc_level_indication,
            length_size_minus_one,
            num_of_sequence_parameter_sets,
            sequence_parameter_sets,
            num_of_picture_parameter_sets,
            picture_parameter_sets,
        )


# ISO/IEC 14496-10:2020(E)
# 7.3.1 NAL unit syntax
# 7.4.1 NAL unit semantics

@attr.s(auto_attribs=True, slots=True, frozen=True)
class NalUnit:
    forbidden_zero_bit: int
    nal_ref_idc: int
    nal_unit_type: int
    # extensions ignored
    rbsp_bytes: bytes


class NalUnitParser:
    def parse(self, data: bytes) -> NalUnit:
        stream = io.BytesIO(data)
        reader = StructReader(stream)

        byte = reader.read_ui8()
        forbidden_zero_bit = byte >> 7
        nal_ref_idc = (byte >> 5) & 0b0000_0011
        nal_unit_type = byte & 0b0001_1111

        # extensions ignored
        if nal_unit_type in (14, 20, 21):
            raise NotImplementedError()
        nal_unit_header_bytes = 1

        i = nal_unit_header_bytes
        num_bytes_in_nal_unit = len(data)
        rbsp_bytes_io = io.BytesIO()

        while i < num_bytes_in_nal_unit:
            with OffsetRepositor(stream):
                try:
                    next_24_bits = reader.read(3)
                except EOFError:
                    next_24_bits = b'0'

            if i + 2 < num_bytes_in_nal_unit and next_24_bits == 0x000003:
                rbsp_bytes_io.write(reader.read(2))
                emulation_prevention_three_byte = reader.read(1)
                assert emulation_prevention_three_byte == 0x03
                i += 3
            else:
                rbsp_bytes_io.write(reader.read(1))
                i += 1

        rbsp_bytes = rbsp_bytes_io.getvalue()

        return NalUnit(
            forbidden_zero_bit,
            nal_ref_idc,
            nal_unit_type,
            rbsp_bytes,
        )


# ISO/IEC 14496-10:2020(E)
# 7.3.2.1.1 Sequence parameter set data syntax
# 7.4.2.1.1 Sequence parameter set data semantics

# Table 6-1 – SubWidthC, and SubHeightC values derived from
# chroma_format_idc and separate_colour_plane_flag
SUB_WIDTH_HEIGHT_MAPPING: Final = {
    1: (2, 2),
    2: (2, 1),
    3: (1, 1),
}


@attr.s(auto_attribs=True, slots=True, frozen=True)
class SequenceParameterSetData:
    profile_idc: int
    constraint_set0_flag: int
    constraint_set1_flag: int
    constraint_set2_flag: int
    constraint_set3_flag: int
    constraint_set4_flag: int
    constraint_set5_flag: int
    level_idc: int
    seq_parameter_set_id: int
    chroma_format_idc: int
    separate_colour_plane_flag: int
    bit_depth_luma_minus8: int
    bit_depth_chroma_minus8: int
    qpprime_y_zero_transform_bypass_flag: int
    seq_scaling_matrix_present_flag: int
    seq_scaling_list_present_flag: List[int]
    log2_max_frame_num_minus4: int
    pic_order_cnt_type: int
    log2_max_pic_order_cnt_lsb_minus4: int
    delta_pic_order_always_zero_flag: int
    offset_for_non_ref_pic: int
    offset_for_top_to_bottom_field: int
    num_ref_frames_in_pic_order_cnt_cycle: int
    offset_for_ref_frame: List[int]
    max_num_ref_frames: int
    gaps_in_frame_num_value_allowed_flag: int
    pic_width_in_mbs_minus1: int
    pic_height_in_map_units_minus1: int
    frame_mbs_only_flag: int
    mb_adaptive_frame_field_flag: int
    direct_8x8_inference_flag: int
    frame_cropping_flag: int
    frame_crop_left_offset: int
    frame_crop_right_offset: int
    frame_crop_top_offset: int
    frame_crop_bottom_offset: int
    vui_parameters_present_flag: int

    @property
    def chroma_array_type(self) -> int:
        if self.separate_colour_plane_flag == 0:
            return self.chroma_format_idc
        return 0

    @property
    def sub_width_c(self) -> int:
        assert (
            self.chroma_format_idc in (1, 2, 3) and
            self.separate_colour_plane_flag == 0
        ), 'SubWidthC undefined!'
        return SUB_WIDTH_HEIGHT_MAPPING[self.chroma_format_idc][0]

    @property
    def sub_height_c(self) -> int:
        assert (
            self.chroma_format_idc in (1, 2, 3) and
            self.separate_colour_plane_flag == 0
        ), 'SubHeightC undefined!'
        return SUB_WIDTH_HEIGHT_MAPPING[self.chroma_format_idc][1]

    @property
    def mb_width_c(self) -> int:
        if self.chroma_format_idc == 0 or self.separate_colour_plane_flag == 1:
            return 0
        return 16 // self.sub_width_c

    @property
    def mb_height_c(self) -> int:
        if self.chroma_format_idc == 0 or self.separate_colour_plane_flag == 1:
            return 0
        return 16 // self.sub_height_c

    @property
    def pic_width_in_mbs(self) -> int:
        return self.pic_width_in_mbs_minus1 + 1

    @property
    def pic_width_in_samples_l(self) -> int:
        return self.pic_width_in_mbs * 16

    @property
    def pic_width_in_samples_c(self) -> int:
        return self.pic_width_in_mbs * self.mb_width_c

    @property
    def pic_height_in_map_units(self) -> int:
        return self.pic_height_in_map_units_minus1 + 1

    @property
    def pic_size_in_map_units(self) -> int:
        return self.pic_width_in_mbs * self.pic_height_in_map_units

    @property
    def frame_height_in_mbs(self) -> int:
        return (2 - self.frame_mbs_only_flag) * self.pic_height_in_map_units

    @property
    def crop_unit_x(self) -> int:
        if self.chroma_array_type == 0:
            return 1
        return self.sub_width_c

    @property
    def crop_unit_y(self) -> int:
        if self.chroma_array_type == 0:
            return 2 - self.frame_mbs_only_flag
        return self.sub_height_c * (2 - self.frame_mbs_only_flag)

    @property
    def frame_width(self) -> int:
        x0 = self.crop_unit_x * self.frame_crop_left_offset
        x1 = self.pic_width_in_samples_l - \
            (self.crop_unit_x * self.frame_crop_right_offset + 1)
        return x1 - x0 + 1  # x1 inclusive

    @property
    def frame_height(self) -> int:
        y0 = self.crop_unit_y * self.frame_crop_top_offset
        y1 = 16 * self.frame_height_in_mbs - \
            (self.crop_unit_y * self.frame_crop_bottom_offset + 1)
        return y1 - y0 + 1  # y1 inclusive


class SequenceParameterSetRBSPParser:
    def parse(self, rbsp: bytes) -> SequenceParameterSetData:
        bits = bitarray()
        bits.frombytes(rbsp)
        bits_reader = BitsReader(bits)
        egc_reader = ExpGolombCodeReader(bits_reader)

        profile_idc = bits_reader.read_bits_as_int(8)
        constraint_set0_flag = bits_reader.read_bits_as_int(1)
        constraint_set1_flag = bits_reader.read_bits_as_int(1)
        constraint_set2_flag = bits_reader.read_bits_as_int(1)
        constraint_set3_flag = bits_reader.read_bits_as_int(1)
        constraint_set4_flag = bits_reader.read_bits_as_int(1)
        constraint_set5_flag = bits_reader.read_bits_as_int(1)
        reserved_zero_2bits = bits_reader.read_bits_as_int(2)
        assert reserved_zero_2bits == 0
        level_idc = bits_reader.read_bits_as_int(8)
        seq_parameter_set_id = egc_reader.read_ue()

        # 7.4.2.1.1 Sequence parameter set data semantics
        # When chroma_format_idc is not present, it shall be inferred to be
        # equal to 1 (4:2:0 chroma format).
        chroma_format_idc = 1
        # When separate_colour_plane_flag is not present, it shall be
        # inferred to be equal to 0.
        separate_colour_plane_flag = 0
        # When bit_depth_luma_minus8 is not present, it shall be inferred to be
        # equal to 0. bit_depth_luma_minus8 shall be in the range of 0 to 6,
        # inclusive.
        bit_depth_luma_minus8 = 0
        # When bit_depth_chroma_minus8 is not present, it shall be inferred to
        # be equal to 0. bit_depth_chroma_minus8 shall be in the range of 0 to
        # 6, inclusive.
        bit_depth_chroma_minus8 = 0
        # When qpprime_y_zero_transform_bypass_flag is not present, it shall be
        # inferred to be equal to 0.
        qpprime_y_zero_transform_bypass_flag = 0
        # When seq_scaling_matrix_present_flag is not present, it shall be
        # inferred to be equal to 0.
        seq_scaling_matrix_present_flag = 0
        seq_scaling_list_present_flag = []

        if profile_idc in (
            100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135
        ):
            chroma_format_idc = egc_reader.read_ue()
            if chroma_format_idc == 3:
                separate_colour_plane_flag = bits_reader.read_bits_as_int(1)
            bit_depth_luma_minus8 = egc_reader.read_ue()
            bit_depth_chroma_minus8 = egc_reader.read_ue()
            qpprime_y_zero_transform_bypass_flag = \
                bits_reader.read_bits_as_int(1)
            seq_scaling_matrix_present_flag = bits_reader.read_bits_as_int(1)
            if seq_scaling_matrix_present_flag:
                for i in range(8 if chroma_format_idc != 3 else 12):
                    flag = bits_reader.read_bits_as_int(1)
                    seq_scaling_list_present_flag.append(flag)
                    if not flag:
                        continue
                    self._scaling_list(egc_reader, 16 if i < 6 else 64)

        log2_max_frame_num_minus4 = egc_reader.read_ue()
        pic_order_cnt_type = egc_reader.read_ue()

        log2_max_pic_order_cnt_lsb_minus4 = 0
        delta_pic_order_always_zero_flag = 1
        offset_for_non_ref_pic = 0
        offset_for_top_to_bottom_field = 0
        num_ref_frames_in_pic_order_cnt_cycle = 0
        offset_for_ref_frame = []

        if pic_order_cnt_type == 0:
            log2_max_pic_order_cnt_lsb_minus4 = egc_reader.read_ue()
        elif pic_order_cnt_type == 1:
            delta_pic_order_always_zero_flag = bits_reader.read_bits_as_int(1)
            offset_for_non_ref_pic = egc_reader.read_se()
            offset_for_top_to_bottom_field = egc_reader.read_se()
            num_ref_frames_in_pic_order_cnt_cycle = egc_reader.read_ue()
            offset_for_ref_frame = [
                egc_reader.read_se()
                for _ in range(num_ref_frames_in_pic_order_cnt_cycle)
            ]

        max_num_ref_frames = egc_reader.read_ue()
        gaps_in_frame_num_value_allowed_flag = bits_reader.read_bits_as_int(1)
        pic_width_in_mbs_minus1 = egc_reader.read_ue()
        pic_height_in_map_units_minus1 = egc_reader.read_ue()
        frame_mbs_only_flag = bits_reader.read_bits_as_int(1)

        # When mb_adaptive_frame_field_flag is not present, it shall be
        # inferred to be equal to 0.
        mb_adaptive_frame_field_flag = 0

        if not frame_mbs_only_flag:
            mb_adaptive_frame_field_flag = bits_reader.read_bits_as_int(1)

        direct_8x8_inference_flag = bits_reader.read_bits_as_int(1)
        frame_cropping_flag = bits_reader.read_bits_as_int(1)

        # When frame_cropping_flag is equal to 0, the values of
        # frame_crop_left_offset, frame_crop_right_offset,
        # frame_crop_top_offset, and frame_crop_bottom_offset shall be
        # inferred to be equal to 0.
        frame_crop_left_offset = 0
        frame_crop_right_offset = 0
        frame_crop_top_offset = 0
        frame_crop_bottom_offset = 0

        if frame_cropping_flag:
            frame_crop_left_offset = egc_reader.read_ue()
            frame_crop_right_offset = egc_reader.read_ue()
            frame_crop_top_offset = egc_reader.read_ue()
            frame_crop_bottom_offset = egc_reader.read_ue()

        vui_parameters_present_flag = bits_reader.read_bits_as_int(1)

        if vui_parameters_present_flag:
            # vui_parameters ignored
            pass

        # rbsp_trailing_bits ignored

        return SequenceParameterSetData(
            profile_idc,
            constraint_set0_flag,
            constraint_set1_flag,
            constraint_set2_flag,
            constraint_set3_flag,
            constraint_set4_flag,
            constraint_set5_flag,
            level_idc,
            seq_parameter_set_id,
            chroma_format_idc,
            separate_colour_plane_flag,
            bit_depth_luma_minus8,
            bit_depth_chroma_minus8,
            qpprime_y_zero_transform_bypass_flag,
            seq_scaling_matrix_present_flag,
            seq_scaling_list_present_flag,
            log2_max_frame_num_minus4,
            pic_order_cnt_type,
            log2_max_pic_order_cnt_lsb_minus4,
            delta_pic_order_always_zero_flag,
            offset_for_non_ref_pic,
            offset_for_top_to_bottom_field,
            num_ref_frames_in_pic_order_cnt_cycle,
            offset_for_ref_frame,
            max_num_ref_frames,
            gaps_in_frame_num_value_allowed_flag,
            pic_width_in_mbs_minus1,
            pic_height_in_map_units_minus1,
            frame_mbs_only_flag,
            mb_adaptive_frame_field_flag,
            direct_8x8_inference_flag,
            frame_cropping_flag,
            frame_crop_left_offset,
            frame_crop_right_offset,
            frame_crop_top_offset,
            frame_crop_bottom_offset,
            vui_parameters_present_flag,
        )

    def _scaling_list(
        self, egc_reader: ExpGolombCodeReader, list_size: int
    ) -> None:
        # 7.3.2.1.1.1 Scaling list syntax
        # scalingList and useDefaultScalingMatrixFlag ignored
        last_scale = next_scale = 8
        for _ in range(list_size):
            if next_scale != 0:
                delta_scale = egc_reader.read_se()
                next_scale = (last_scale + delta_scale + 256) % 256
            if next_scale != 0:
                last_scale = next_scale


# ISO/IEC 14496-10:2020(E)
# 9.1 Parsing process for Exp-Golomb codes
# 9.1.1 Mapping process for signed Exp-Golomb codes

class ExpGolombCodeReader:
    def __init__(self, reader: BitsReader) -> None:
        self._reader = reader

    def read_ue(self) -> int:
        zero_bit = bitarray('0')
        leading_zero_bits = 0

        while True:
            bit = self._reader.read_bits(1)
            if bit == zero_bit:
                leading_zero_bits += 1
            else:
                break

        return (
            2 ** leading_zero_bits - 1 +
            self._reader.read_bits_as_int(leading_zero_bits)
        )

    def read_se(self) -> int:
        code_num = self.read_ue()
        value = -1 ** (code_num + 1) * math.ceil(code_num / 2)
        result = value if code_num % 2 == 0 else abs(value)
        return result


def extract_resolution(packet: bytes) -> Tuple[int, int]:
    """Extract resolution from AVCDecoderConfigurationRecord packet."""
    record = AVCSequenceHeaderParser().parse(packet)
    sps = record.sequence_parameter_sets[0]
    nal_unit = NalUnitParser().parse(sps.sequence_parameter_set_nal_unit)
    sps_data = SequenceParameterSetRBSPParser().parse(nal_unit.rbsp_bytes)
    return sps_data.frame_width, sps_data.frame_height
