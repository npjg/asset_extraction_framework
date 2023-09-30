
from dataclasses import dataclass
import logging
import io
from enum import Enum, Flag
from typing import List

import self_documenting_struct as struct
from self_documenting_struct import Type

# https://github.com/rolinh/libgwavi/blob/master/src/gwavi.c

## The type of the stream must be presented in the stream header.
## These are the types defined by default. There may be others.
@dataclass
class AviStreamType:
    Audio = b'auds'
    Midi = b'mids'
    Text = b'txts'
    Video = b'vids'

## A stream type also must be presented in the FourCCs for 
## each chunk that contains the actual stream data:
##  [StreamId][TwoCC]
##   ^^^^^^^^  ^^^^^
##   |         - One of the below two-character codes
##   - The ID of the stream as a two-digit integer in ASCII
## For example, if stream 0 contains audio, the data chunks 
## for that stream would have the FourCC '00wb'. If stream 1 contains
## video, the data chunks for that stream would have the FourCC '01db' or '01dc'.
@dataclass 
class AviStreamTwoCC:
    UncompressedVideo = b'db'
    CompressedVideo = b'dc'
    PaletteChange = b'pc'
    Audio = b'wb'

## A simple AVI file that has:
##  - A single video stream (compressed or uncompressed), and
##  - A single WAVE_FORMAT_PCM audio stream. 
## This is the default asset export format for animations.
##
## I wrote this custom AVI generator because the other methods for generating
## AVI files were far too slow for the scale required for asset exporting:
## - Too slow for the human to set up (like pyAV), or
## - Too slow for the computer to run (like shelling out to ffmpeg).
##
## Currently write-only because that's all that I needed for asset exports.
##
## Sources:
## - https://learn.microsoft.com/en-us/windows/win32/directshow/avi-riff-file-reference
## - https://github.com/tpn/winsdk-10/blob/master/Include/10.0.14393.0/um/AviFmt.h
## - https://github.com/tpn/winsdk-10/blob/master/Include/10.0.14393.0/shared/mmreg.h
class AviFile:
    def __init__(self):
        # DEFINE THE MAIN AVI HEADER.
        self.main_header = AviMainHeader()

        # DEFINE THE AUDIO STREAM.
        self.audio_stream_header = None
        self.wave_header = None
        self.audio_chunks = []

        # DEFINE THE VIDEO STREAM.
        self.video_stream_header = None
        self.video_chunks = []

    ## Initializes the audio stream. This need be done only once per AVI file.
    ## \param[in] channel_count - The number of channels in the audio.
    ## \param[in] samples_per_second - The number of samples per second in the audio.
    ## \param[in] bits_per_sample - The number of bits per sample.
    def initialize_audio_stream(self, channel_count: int, samples_per_second: int, bits_per_sample: int):
        # CREATE THE STREAM HEADER.
        self.audio_stream_header = AviStreamHeader()
        self.audio_stream_header.stream_type = AviStreamType.Audio
        self.audio_stream_header.rate = samples_per_second

        # CREATE THE STREAM FORMAT HEADER.
        self.wave_header = PcmWaveFormatEx()
        self.wave_header.channel_count = channel_count
        self.wave_header.samples_per_second = samples_per_second
        self.wave_header.bits_per_sample = bits_per_sample

    ## Add an audio chunk to the single audio stream of the AVI file.
    ## \param[in] sound - The sound to add to the audio stream.
    def add_audio_chunk(self, sound: 'Sound'):
        # CREATE THE CHUNK.
        chunk_fourcc = b'01' + AviStreamTwoCC.Audio
        self.audio_chunks.append((chunk_fourcc, sound.pcm))

    ## Initializes the video stream. This need be done only once per AVI file.
    ## The following requirements must be followed:
    ##  - Each frame in the video stream must have the same width and height.
    ## \param[in] width - The width of the video stream.
    ##            Each frame in the video stream must have the same dimensions.
    ## \param[in] height - The height of the video stream.
    ##            Each frame in the video stream must have the same dimensions.
    ## \param[in] frames_per_second - The framerate of this video stream.
    ## \param[in] bits_per_pixel - The color depth of the video stream (usually 8).
    ## \param[in] palette - The palette for the video stream, if necessary.
    ##            (Palette changes are currently not supported.)
    def initialize_video_stream(self, width, height, frames_per_second, bits_per_pixel, palette):
        # CREATE THE STREAM HEADER.
        self.video_stream_header = AviStreamHeader()
        self.video_stream_header.stream_type = AviStreamType.Video
        self.video_stream_header.rate = frames_per_second
        self.video_stream_header.stream_rectangle[2] = width
        self.video_stream_header.stream_rectangle[3] = -height
        self.video_stream_header.stream_size = 0

        # CREATE THE STREAM FORMAT HEADER.
        self.bitmap_header = BitmapInfo()
        self.bitmap_header.width = width
        self.bitmap_header.height = -height
        self.bitmap_header.bits_per_pixel = bits_per_pixel
        # Then the palette must be added.
        # The palette must be in blue-green-red color order.
        if palette is not None:
            self.bitmap_header.palette = bytes(palette)

        # SET THE MAIN HEADER.
        MICROSECONDS_PER_SECOND = 1000000
        self.main_header.micro_seconds_per_frame = MICROSECONDS_PER_SECOND // frames_per_second
        self.main_header.width = width
        self.main_header.height = -height
    
    ## Add a single bitmap to the single video stream of the AVI file.
    ## \param[in] image - The bitmap to add to the video stream.
    def add_video_frame(self, bitmap: 'Image'):
        # CREATE THE CHUNK.
        chunk_fourcc = b'00' + AviStreamTwoCC.UncompressedVideo
        self.video_chunks.append((chunk_fourcc, bitmap.tobytes()))
        self.video_stream_header.stream_size += 1

    ## Writes the AVI file to the given filepath.
    ## \param[in] filepath - The filepath where the file should be written.
    def write(self, filepath: str):
        # DEFINE THE FILE STRUCTURE.
        # The RIFF file structure is defined as potentially nested lists of 2-tuples:
        # The first element defines the FourCC for the entry, and the second element
        # defines the contents of the entry.
        riff_structure = [
            (b'AVI ', [
                (b'hdrl', [
                    (b'avih', self.main_header),
                    (b'strl', [
                        (b'strh', self.video_stream_header),
                        (b'strf', self.bitmap_header)]),
                    (b'strl', [
                        (b'strh', self.audio_stream_header),
                        (b'strf', self.wave_header)])]),
                (b'movi', [
                    *self.video_chunks, *self.audio_chunks])])]

        # WRITE THE FILE.
        with open(filepath, 'wb') as avi_file:
            self._write_list(avi_file, list_fourcc = b'RIFF', list_name = b'AVI ', list_structure = riff_structure)

    ## Writes a chunk that can contain subchunks to the stream at the current position.
    ##  - FourCC (literal 4 bytes) [usually "LIST" or "RIFF"]
    ##  - Size (as uint32_le)
    ##  - Subchunk(s)
    ## \param[in,out] stream - A writable binary stream.
    ## \param[in] list_structure - A potentially nested list of 2-tuples:
    ##  - The first entry provides the name 
    ##  - If the second entry is a list, a LIST entry is created:
    ##   - LIST (literal 4 bytes)
    ##   - Size (as uint32_le)
    ##   - FourCC (4 bytes)
    ##  - Otherwise, a standard chunk is created:
    ##   - FourCC (4 bytes)
    ##   - Size (as uint32_le)
    ## \param[in] list_fourcc - 
    def _write_list(self, stream, list_name, list_structure, list_fourcc = b'LIST'):
        # WRITE A PLACEHOLDER FOR THE CHUNK SIZE.
        stream.write(list_fourcc)
        size_pointer = stream.tell()
        stream.write(b'\x00\x00\x00\x00')

        # WRITE THE SUBCHUNK NAME.
        content_start_pointer = stream.tell()
        stream.write(list_name)

        # WRITE THE ELEMENTS OF THIS LIST.
        for entry in list_structure:
            if isinstance(entry[1], list):
                self._write_list(stream, entry[0], entry[1])
            else:
                self._write_chunk(stream, entry[0], entry[1])

        # WRITE THE LIST SIZE.
        list_size = stream.tell() - content_start_pointer
        current_position = stream.tell()
        stream.seek(size_pointer)
        struct.pack.uint32_le(list_size, into = stream)
        stream.seek(current_position)

    ## Writes one FourCC chunk to the stream at the current position.
    ## \param[in] stream - A writable binary stream where the FourCC chunk
    ##            should be written.
    ## \param[in] chunk_name - The name of the chunk as a FourCC.
    ## \param[in] chunk_data - The actual data of the chunk.
    def _write_chunk(self, stream, chunk_name: bytes, chunk_data: bytes):
        if chunk_data is None:
            return

        # WRITE THE CHUNK NAME.
        stream.write(chunk_name)
        if isinstance(chunk_data, bytes):
            # WRITE THE CHUNK SIZE.
            struct.pack.uint32_le(len(chunk_data), into = stream)

            # WRITE THE CHUNK.
            stream.write(chunk_data)
        else:
            # WRITE A PLACEHOLDER FOR THE CHUNK SIZE.
            size_pointer = stream.tell()
            stream.write(b'\x00\x00\x00\x00')

            # WRITE THE CHUNK.
            content_start_pointer = stream.tell()
            chunk_data.encode(stream)

            # WRITE THE CHUNK SIZE.
            list_size = stream.tell() - content_start_pointer
            current_position = stream.tell()
            stream.seek(size_pointer)
            struct.pack.uint32_le(list_size, into = stream)
            stream.seek(current_position)

        # The data chunks can reside directly in the 'movi' list, or
        # they might be grouped within 'rec ' lists. The 'rec ' grouping 
        # implies that the grouped chunks should be read from disk all at
        # once, and is intended for files that are interleaved to play 
        # from CD-ROM.

## Defines information for the whole AVI file.
@dataclass
class AviMainHeader:
    # The overall timing for the file.
    micro_seconds_per_frame = None     
    
    # The approximate maximum data rate of the file. 
    # This value indicates the number of bytes per second
    # the system must handle to present an AVI sequence as 
    # specified by the other parameters contained in the main
    # header and stream header chunks.
    max_bytes_per_second = 0

    # Pad the data to multiples of this value.
    padding_in_bytes = 1

    # There are multiple possible flags here,
    # but none of them are needed for this simple implementation.
    flags = 0

    # The total number of frames of data in this file.
    total_frames = 0

    # For interleaved files, specify the number of frames in 
    # the file prior to the initial frame of the AVI sequence.
    # Noninterleaved files should specify zero.
    #
    # For this simple implementation, zero is good enough.
    initial_frames = 0

    # The number of streams in the file. 
    # A file with audio and video has two streams.
    stream_count = 1

    # this size should be large enough to contain the largest chunk in the file. 
    # If set to zero, or if it is too small, the playback software will have to 
    # reallocate memory during playback, which will reduce performance. For an 
    # interleaved file, the buffer size should be large enough to read an entire 
    # record, and not just a chunk.
    #
    # For this simple implementation for modern hardware, zero is good enough.
    suggested_buffer_size = 0

    # The dimensions, in pixels, of the animation.
    # If left as None, they will be set to the 
    width = None
    height = None

    # These should always be zero.
    reserved = [0, 0, 0, 0]

    ## Writes this structure to a writable stream.
    ## \param[in,out] stream - The stream where the structure should be written
    def encode(self, stream):
        struct.pack.from_list((
            (Type.uint32_le, self.micro_seconds_per_frame),
            (Type.uint32_le, self.max_bytes_per_second),
            (Type.uint32_le, self.padding_in_bytes),
            (Type.uint32_le, self.flags),
            (Type.uint32_le, self.total_frames),
            (Type.uint32_le, self.initial_frames),
            (Type.uint32_le, self.stream_count),
            (Type.uint32_le, self.suggested_buffer_size),
            (Type.int32_le, self.width),
            (Type.int32_le, self.height),
            (Type.uint32_le, self.reserved[0]),
            (Type.uint32_le, self.reserved[1]),
            (Type.uint32_le, self.reserved[2]),
            (Type.uint32_le, self.reserved[3]),
        ), into = stream)

## An bitmap header to represent an uncompressed bitmap.
## One of the potential AVI stream headers.
@dataclass
class BitmapInfo:
    # BitmapInfoHeader.
    STRUCTURE_SIZE = 0x28
    width = None
    height = None
    planes = 1 # Must be set to 1.
    bits_per_pixel = None
    compression = 0
    ## This can be set to 0 for uncompressed RGB bitmaps.
    image_length = 0
    horizontal_resolution = 0
    vertical_resolution = 0
    used_colors = 0
    important_colors = 0

    # Palette information.
    palette: bytes = None

    ## Writes this structure to a writable stream.
    ## \param[in,out] stream - The stream where the structure should be written.
    def encode(self, stream):
        struct.pack.from_list((
            (Type.uint32_le, self.STRUCTURE_SIZE),
            (Type.int32_le, self.width),
            (Type.int32_le, self.height),
            (Type.uint16_le, self.planes),
            (Type.uint16_le, self.bits_per_pixel),
            (Type.uint32_le, self.compression),
            (Type.uint32_le, self.image_length),
            (Type.uint32_le, self.horizontal_resolution),
            (Type.uint32_le, self.vertical_resolution), 
            (Type.uint32_le, self.used_colors),
            (Type.uint32_le, self.important_colors)
        ), into = stream)

        if self.palette:
            stream.write(self.palette)

## Encodes a waveform format structure specifically for PCM data.
## This can be expanded later if other formats must be supported.
## One of the potential AVI stream headers.
@dataclass
class PcmWaveFormatEx:
    format_tag = 1 # WAVE_FORMAT_PCM.
    channel_count = None
    samples_per_second = None
    bits_per_sample = None

    # Size, in bytes, of extra format information appended
    # to the end of the WAVEFORMATEX structure. For raw PCM
    # formats, this is ignored so it can be set to zero.
    additional_information_size = 0

    # The minimum atomic unit of data for this format.
    # Software must process a multiple of these bytes of data at a time. 
    # Data written to and read from a device must always start at the beginning of a block.
    @property
    def block_alignment(self) -> int:
        return self.channel_count * self.bits_per_sample

    # (For non-PCM formats, this member must be computed according to the
    #  manufacturer's specification of the format tag.)
    @property
    def average_bytes_per_second_transfer_rate(self) -> int:
        return self.samples_per_second * self.block_alignment

    ## Writes this structure to a writable stream.
    ## \param[in,out] stream - The stream where the structure should be written.
    def encode(self, stream):
        struct.pack.from_list((
            (Type.uint16_le, self.format_tag),
            (Type.uint16_le, self.channel_count),
            (Type.uint32_le, self.samples_per_second),
            (Type.uint32_le, self.average_bytes_per_second_transfer_rate),
            (Type.uint16_le, self.block_alignment),
            (Type.uint16_le, self.bits_per_sample),
            (Type.uint16_le, self.additional_information_size)
        ), into = stream)

## Defines one stream.
@dataclass
class AviStreamHeader:
    ## The bits in the high-order word of these flags are 
    ## specific to the type of data contained in the stream. 
    ## The following standard flags are defined.
    #@dataclass
    #class AviStreamFlags:
    #    ## This stream should not be enabled by default.
    #    AVISF_DISABLED,
    #    ## This video stream contains palette changes.
    #    AVISF_VIDEO_PALCHANGES

    FOURCC: bytes = b'strh'
    STRUCTURE_SIZE: int = 0

    # A FOURCC that identifies the stream type.
    stream_type: bytes = None

    # Optionally, contains a FOURCC that identifies a specific data handler. 
    # The data handler is the preferred handler for the stream. For audio and 
    # video streams, this specifies the codec for decoding the stream.
    stream_data_handler: bytes = b'DIB '

    # There are multiple possible flags here,
    # but none of them are needed for this simple implementation.
    flags: int = 0

    # For example, in a file with multiple audio streams, the one
    # with the highest priority might be the default stream.
    # I don't know what this actually does and it isn't needed for
    # this implementation.
    priority: int = 0

    # The language of the stream.
    language: int = 0

    # The number of frames in the file prior to the
    # initial frame of this AVI sequence.
    #
    # Since we are not creating interleaved files for
    # this implementation, this can be zero.
    frames_before_this_stream: int = 0

    # The time scale used by this stream.
    # By default, we will use a unit of one second.
    scale = 1
    # The data rate of this stream.
    rate = None

    # Specifies the starting time for this stream. 
    # The units are defined by the dwRate and dwScale 
    # members in the main file header.
    #
    # Because there will generally be only one audio
    # stream of each type, we can default to starting
    # the stream at zero.
    start_time = 0

    # Specifies the length of this stream. The units are
    # defined by the rate and scale members in this header.
    # Typically the units are just bytes.
    stream_size = 0

    # Specifies how large a buffer should be used to read this stream. 
    # Either zero or the size of the largest chunk present in the stream.
    suggested_buffer_size = 0

    # Generally only used for compressed data.
    # If set to –1, drivers use the default quality value.
    quality = -1

    # The size of a single sample of data, like an audio sample or video frame.
    # For video streams, this number is typically zero, although it can be nonzero
    # if all video frames are the same size. For audio streams, this number should 
    # be the same as the nBlockAlign member of the WAVEFORMATEX structure describing 
    # the audio.
    sample_size = 0

    # The destination rectangle for a text or video stream within the main rectangle.
    stream_rectangle = [0, 0, 0, 0]

    # For video streams, this is the frame rate. For audio streams, 
    # this rate corresponds to the time needed to play nBlockAlign 
    # bytes of audio, which for PCM audio is the just the sample rate.
    @property
    def samples_per_second(self) -> float:
        return self.rate / self.scale

    ## Writes this structure to a writable stream.
    ## \param[in,out] stream - The stream where the structure should be written.
    def encode(self, stream):
        stream.write(self.stream_type)
        stream.write(self.stream_data_handler)
        struct.pack.from_list((
            (Type.uint32_le, self.flags),
            (Type.uint16_le, self.priority),
            (Type.uint16_le, self.language),
            (Type.uint32_le, self.frames_before_this_stream),
            (Type.uint32_le, self.scale),
            (Type.uint32_le, self.rate),
            (Type.uint32_le, self.start_time),
            (Type.uint32_le, self.stream_size),
            (Type.uint32_le, self.suggested_buffer_size),
            (Type.int32_le, self.quality),
            (Type.uint32_le, self.sample_size),
            (Type.int16_le, self.stream_rectangle[0]),
            (Type.int16_le, self.stream_rectangle[1]),
            (Type.int16_le, self.stream_rectangle[2]),
            (Type.int16_le, self.stream_rectangle[3]),
        ), into = stream)