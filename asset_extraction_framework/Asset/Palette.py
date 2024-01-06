
from io import BytesIO
from functools import lru_cache

from .Asset import Asset

## An RGB color palette.
class RgbPalette(Asset):
    ## Parse a palette from binary data in a file and reproduce it in various forms.
    ## \param[in,out] file - The file from which to read data, with the stream
    ##            at the starting byte of the palette.
    ## \param[in] total_palette_entries - The total number of color entries
    ##            to read. Each color entry has a red, green, and blue color entry.
    ## \param[in] blue_green_red_order - If True, indicate colors are ordered BGR in the stream.
    ##            Otherwise, indicate colors are ordered standard RGB.
    def __init__(self, stream, has_entry_alignment: bool, total_palette_entries: int = 0x100, blue_green_red_order: bool = False):
        # STORE THE PARAMETERS.
        self._total_palette_entries = total_palette_entries
        self._has_entry_alignment = has_entry_alignment
        self._blue_green_red_order = blue_green_red_order

        # READ THE PALETTE.
        palette_entry_size_in_bytes = 4 if has_entry_alignment else 3
        total_palette_bytes = palette_entry_size_in_bytes * total_palette_entries
        self._raw_bytes = BytesIO(stream.read(total_palette_bytes))

    ## Returns the definition of the palette in blue-green-red (BGR) order.
    ## \param[in] align_entries - Align each color tuple to the dword boundary 
    ##             (32 bits). Since there are only three colors of 8 bits each,
    ##             the last 8 bits should always be zero.
    ## To prevent this rather expensive computation from occurring every time we retrieve
    ## the palette bytes, we will cache the result of this function call with the given args.
    ## Note that this will cause issues if the self._raw_bytes changes between runs, but that isn't expected.
    @lru_cache(maxsize = 2)
    def raw_bgr_bytes(self, align_entries: bool = True) -> bytearray:
        self._raw_bytes.seek(0)
        raw_bgr_bytes = bytearray()
        for index in range(self._total_palette_entries):
            # READ THIS COLOR TUPLE.
            bgr_color_tuple = self._raw_bytes.read(3)
            if self._has_entry_alignment:
                self._raw_bytes.read(1)

            # ENSURE THE COLOR INDEX IS IN BGR ORDER.
            colors_in_rgb_order = not self._blue_green_red_order
            if colors_in_rgb_order:
                # PUT THE COLOR INDEX IN BGR ORDER.
                # The colors are in RGB order, so the blue and the red must be swapped.
                # 
                # The slice notation below is used due to the following behavior:
                #  - bytes[0] -> int (must be re-encoded to bytes, which is wasteful),
                #  - bytes[0:1] -> bytes[0], but still as bytes.
                red_color_index = bgr_color_tuple[0:1]
                green_color_index = bgr_color_tuple[1:2]
                blue_color_index = bgr_color_tuple[2:3]
                bgr_color_tuple = blue_color_index + green_color_index + red_color_index

            # ENSURE THE RIGHT PADDING IS ADDED.
            if align_entries:
                bgr_color_tuple += b'\x00'
                assert len(bgr_color_tuple) == 4
            else:
                assert len(bgr_color_tuple) == 3

            # STORE THIS COLOR TUPLE.
            raw_bgr_bytes += bgr_color_tuple
        return raw_bgr_bytes

    ## To prevent this rather expensive computation from occurring every time we retrieve
    ## the palette bytes, we will cache the result of this function call with the given args.
    ## Note that this will cause issues if the self._raw_bytes changes between runs, but that isn't expected.
    @lru_cache(maxsize = 2)
    def raw_rgb_bytes(self, align_entries: bool = False) -> bytes:
        self._raw_bytes.seek(0)
        raw_rgb_bytes = bytearray()
        for index in range(self._total_palette_entries):
            # READ THIS COLOR TUPLE.
            rgb_color_tuple = self._raw_bytes.read(3)
            if self._has_entry_alignment:
                self._raw_bytes.read(1)

            # ENSURE THE COLOR INDEX IS IN RGB ORDER.
            colors_in_rgb_order = not self._blue_green_red_order
            if not colors_in_rgb_order:
                # PUT THE COLOR INDEX IN RGB ORDER.
                # The colors are in RGB order, so the blue and the red must be swapped.
                # 
                # The slice notation below is used due to the following behavior:
                #  - bytes[0] -> int (must be re-encoded to bytes, which is wasteful),
                #  - bytes[0:1] -> bytes[0], but still as bytes.
                blue_color_index = rgb_color_tuple[0:1]
                green_color_index = rgb_color_tuple[1:2]
                red_color_index = rgb_color_tuple[2:3]
                rgb_color_tuple = red_color_index + green_color_index + blue_color_index

            # ENSURE THE RIGHT PADDING IS ADDED.
            unnecessary_padding_present = (self._has_entry_alignment) and (not align_entries)
            necessary_padding_not_present = (not self._has_entry_alignment) and (align_entries)
            if unnecessary_padding_present:
                # REMOVE THE PADDING BYTE.
                rgb_color_tuple = rgb_color_tuple[0:4]
            elif necessary_padding_not_present:
                rgb_color_tuple += b'\x00'

            # STORE THIS COLOR TUPLE.
            raw_rgb_bytes += rgb_color_tuple
        return raw_rgb_bytes