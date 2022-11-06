
from .Asset import Asset

## An RGB color palette.
class RgbPalette(Asset):
    ## Parse a palette from binary data in a file.
    ## \param[in,out] file - The file from which to read data, with the stream
    ##            at the starting byte of the palette.
    ## \param[in] expected_total_entries - The total number of color entries
    ##            to read. Each color entry has a red, green, and blue color entry.
    ## \param[in] blue_green_red_order - If True, colors are read in this order.
    ##            Otherwise, colors are read in the standard RGB order.
    def __init__(self, file, expected_total_entries = 0x100, blue_green_red_order = False):
        # READ THE PALETTE.
        self.rgb_colors: bytes = b''
        for palette_index in range(expected_total_entries):
            # READ THIS COLOR ENTRY.
            red_green_blue_color_bytes = bytearray(file.stream.read(3))
            if blue_green_red_order:
                red_green_blue_color_bytes.reverse()
            self.rgb_colors += red_green_blue_color_bytes

            # READ THE PADDING BYTE.
            # The colors are padded to align with the dword boundary (32 bits).
            # Thus, since there are only three colors of 8 bits each,
            # the last 8 bits should always be zero.
            file.stream.read(1)
