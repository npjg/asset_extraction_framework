
from math import ceil
from typing import Optional

from PIL import Image

from .Asset import Asset
from ..Asserts import assert_equal
from .Palette import RgbPalette
from .BoundingBox import BoundingBox

## A paletted, rectangular image with 2D pixels.
class RectangularBitmap(Asset):
    def __init__(self):
        super().__init__()

        # DEFINE A FIELD FOR RAW DATA FROM THE FILE.
        # This data probably needs to, at least, be uncompressed
        # before an image can be shown.
        self.raw: Optional[bytes] = None

        # DEFINE A FIELD FOR THE UNCOMPRESSED PIXELS.
        # Any custom decompressor outputs the raw pixel array here.
        # This array should have size (width * height) bytes.
        # The image property uses these pixels to construct a complete image
        # with the proper palette and dimensions.
        self.pixels: Optional[bytes] = None

        # DEFINE A FIELD FOR THE PALETTE.
        self.palette: Optional[RgbPalette] = None

        # DEFINE FIELDS FOR REQUIRED IMAGE METADATA.
        # The image cannot be exported without these required properties.
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        # The default color depth is 8 bits (2^8 = 256 colors).
        self.bits_per_pixel: int = 0x08

        # DEFINE IMAGE COORDINATES.
        # WIthout these, the image can only be exported standalone.
        # It cannot be exported with animation framing.
        self._left: Optional[int] = None
        self._top: Optional[int] = None
        self._right: Optional[int] = None
        self._bottom: Optional[int] = None

    ## \return The nominal width of the bitmap.
    ## None if there is not enough information to get this dimension.
    @property
    def width(self) -> Optional[int]:
        if self._width is not None:
            # GET THE EXPLICITLY-DEFINED WIDTH.
            return self._width
        elif (self._left is not None) and (self._right is not None):
            # CALCULATE THE WIDTH FROM COORDINATES.
            return self._right - self._left
        else:
            # RETURN NOTHING.
            # There is not enough information to calculate the width.
            return None

    ## \return The nominal height of the bitmap.
    ## Returns None if there is not enough information to get/calculate this dimension.
    @property
    def height(self) -> Optional[int]:
        if self._height is not None:
            # GET THE EXPLICITLY DEFINED HEIGHT.
            return self._height
        elif (self._top is not None) and (self._bottom is not None):
            # CALCULATE THE HEIGHT FROM COORDINATES.
            return self._bottom - self._top
        else:
            # RETURN NOTHING.
            # There is not enough information to calculate the height.
            return None

    ## \return The top rectangular coordinate of the bitmap, if it is known.
    @property
    def top(self) -> Optional[int]:
        return self._top

    ## \return The left rectangular coordinate of the bitmap, if it is known.
    @property
    def left(self) -> Optional[int]:
        return self._left

    ## \return The right rectangular coordinate of the bitmap.
    ## None if there is not enough information to get this coordinate.
    @property
    def right(self) -> Optional[int]:
        if self._right is not None:
            # GET THE EXPLICITLY DEFINED RIGHT COORDINATE.
            return self._right
        elif (self._left is not None) and (self._width is not None):
            # CALCULATE THE COORDINATE.
            return self._left + self._width
        else:
            # RETURN NOTHING.
            # There is not enough information to calculate this coordinate.
            return None

    ## \return The bottom rectangular coordinate of the bitmap.
    ## None if there is not enough information to get this dimension.
    @property 
    def bottom(self) -> Optional[int]:
        if self._bottom is not None:
            # GET THE EXPLICITLY DEFINED BOTTOM COORDINATE.
            return self._bottom
        elif (self._top is not None) and (self._height is not None):
            # CALCULATE THE COORDINATE.
            return self._top + self._height
        else:
            # RETURN NOTHING.
            # There is not enough information to calculate this coordinate.
            return None

    ## Gets the bounding box for this bitmap.
    @property
    def bounding_box(self) -> BoundingBox:
        return BoundingBox(self.top, self.left, self.bottom, self.right)

    ## Calculates the total number of bytes the uncompressed image
    ## (pixels) should occupy, rounded up to the closest whole byte.
    @property
    def expected_bitmap_length_in_bytes(self) -> int:
        return int(float(self.width * self.height * self.bits_per_pixel) / float(8.))

    ## Returns True if this object contains enough information to
    ## export a bitmap image, false otherwise.
    @property
    def is_valid(self) -> bool:
        return (self.pixels is not None) and \
            (self.width is not None) and \
            (self.height is not None) and \
            (self.bits_per_pixel is not None) and \
            (not self.is_empty)

    # \return True when the image has one zero and one nonzero dimension.
    # The image should not be processed in this state.
    @property
    def is_inconsistent(self) -> bool:
        return (self.width == 0 and self.height != 0) or (self.width != 0 and self.height == 0)

    ## \return True when the uncompressed image pixels have the same length
    ## as the expected length; False otherwise.
    @property
    def has_expected_length(self) -> bool:
        return len(self.pixels) == self.expected_bitmap_length_in_bytes

    ## \return True when the image has no width or height; False otherwise.
    @property
    def is_empty(self) -> bool:
        return (self.width == 0) and (self.height == 0)

    ## \return A properly-sized PIL bitmap from the uncompressed pixels.
    ## None if the bitmap is invalid or does not have the expected length.
    @property
    def bitmap(self) -> Optional[Image.Image]:
        if not self.has_expected_length:
            assert_equal(len(self.pixels), self.expected_bitmap_length_in_bytes, 'pixels length in bytes', warn_not_raise = True)

        # CREATE AN IMAGE ONLY IF THERE IS ENOUGH DATA PRESENT.
        if self.is_valid: #and self.has_expected_length:
            # TODO: Do we assume the image is paletted?
            bitmap = Image.frombytes('P', (self.width, self.height), self.pixels)
            return bitmap
        else:
            # If there are no uncompressed pixels or insufficient dimensions,
            # an image cannot be constructed.
            return None

    ## \return True when this image has raw data; False otherwise.
    @property
    def has_raw_image_data(self) -> bool:
        return (self.raw is not None) and (len(self.raw) > 0)

    ## \return True when this image has uncompressed pixel data; False otherwise.
    @property
    def has_pixels(self) -> bool:
        return (self.pixels is not None) and (len(self.pixels) > 0)

    ## Exports the bitmap in the provided format to the provided filename.
    ## The bitmap can be exported in any format supported by Pillow.
    ## This method also supports two meta-formats:
    ##  - none: Do not export the image. Returns immediately.
    ##  - raw : Instead of exporting the decompressed and paletted image, 
    ##          only write the raw image data read from the file.
    ##          (for debugging/further reverse engineering)
    ## \param[in] filename_without_extension - The full filepath of the desired export
    ##            except the extension. The extension wil be added based on the requested
    ##            export format.
    ## \param[in] command_line_arguments - All the command-line arguments provided to the 
    ##            script that invoked this function.
    def export(self, filename: str, command_line_arguments):
        if command_line_arguments.bitmap_format == 'none':
            # DO NOTHING.
            return
        elif command_line_arguments.bitmap_format == 'raw':
            # WRITE THE RAW BYTES FROM THE FILE.
            if self.has_raw_image_data:
                # Since the exported imageself.pixels is not None will not be openable by 
                # other programs, record some vital information (the 
                # dimensions) in the filename itself for later analysis.
                raw_filename = f'{filename}.{self.width}.{self.height}'
                with open(raw_filename, 'wb') as raw_file:
                    raw_file.write(self.raw)
            # If the image is not compressed, self.raw will have no data.
            # In this case, we want to write self.pixels instead.
            elif self.has_pixels:
                with open(filename, 'wb') as pixels_file:
                    pixels_file.write(self.pixels)
        else:
            # WRITE A VIEWABLE BITMAP FILE WITH PILLOW.
            # The bitmap can be exported in any format supported by Pillow.
            bitmap = self.bitmap
            if bitmap is not None:
                # SET THE PALETTE.
                if self.palette is not None:
                    bitmap.putpalette(self.palette.rgb_colors)

                # SAVE THE PALETTED BITMAP.
                filename_with_extension = f'{filename}.{command_line_arguments.bitmap_format}'
                bitmap.save(filename_with_extension, command_line_arguments.bitmap_format)
            elif self.has_pixels:
                # WRITE THE RAW PIXELS.
                # This is a fallback in case the bitmap cannot be created.
                with open(filename, 'wb') as pixels_file:
                    pixels_file.write(self.pixels)
