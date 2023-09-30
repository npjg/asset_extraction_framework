
import os
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
        # This is raw bitmap data, exactly as it was read from the file.
        # This data probably needs to, at least, be uncompressed
        # before an image can be shown. If the bitmap does not need
        # post-processing like decompression, do not populate this field
        # and put the pixels in self._pixels instead.
        self._raw: Optional[bytes] = None
        # Any custom decompressor outputs the raw pixel array here.
        # This array should have size (width * height) bytes.
        # The image property uses these pixels to construct a complete image
        # with the proper palette and dimensions.
        self._pixels: Optional[bytes] = None
        # A properly-sized PIL bitmap from the uncompressed pixels.
        # Originally, this was a property and was generated directly
        # from the uncompressed pixels. However, if the image is 
        # part of an animation, other code might need to further modify
        # the image generated from the uncompressed pixels - for instance,
        # to give each frame the same dimensions or to apply keyframes.
        # Thus, client code can modify this exportable image however it 
        # sees fit. To create or restore an exportable image from the
        # uncompressed pixels, call 
        self._exportable_image: Optional[Image.Image] = None
        self._palette: Optional[RgbPalette] = None
        # The image cannot be exported without these required properties.
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        # The default color depth is 8 bits (2^8 = 256 colors).
        self._bits_per_pixel: int = 0x08
        # Without these, the image can only be exported standalone.
        # It cannot be exported with animation framing.
        self._left: Optional[int] = None
        self._top: Optional[int] = None
        self._right: Optional[int] = None
        self._bottom: Optional[int] = None
        self._include_in_export: bool = True

    @property
    def pixels(self) -> bytes:
        return self._pixels

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
    def _bounding_box(self) -> BoundingBox:
        return BoundingBox(self.top, self.left, self.bottom, self.right)

    ## Calculates the total number of bytes the uncompressed image
    ## (pixels) should occupy, rounded up to the closest whole byte.
    @property
    def __expected_bitmap_length_in_bytes(self) -> int:
        return int(float(self.width * self.height * self._bits_per_pixel) / float(8.))

    ## Returns True if this object contains enough information to
    ## export a bitmap image, false otherwise.
    @property
    def __is_valid(self) -> bool:
        return (self.pixels is not None) and \
            (self.width is not None) and \
            (self.height is not None) and \
            (self._bits_per_pixel is not None) and \
            (not self.__is_empty)

    ## \return True when the uncompressed image pixels have the same length
    ## as the expected length; False otherwise.
    @property
    def __has_expected_length(self) -> bool:
        return len(self.pixels) == self.__expected_bitmap_length_in_bytes

    ## \return True when the image has no width or height; False otherwise.
    @property
    def __is_empty(self) -> bool:
        return (self.width == 0) and (self.height == 0)

    ## \return True when this image has raw data; False otherwise.
    @property
    def __has_raw_image_data(self) -> bool:
        return (self._raw is not None) and (len(self._raw) > 0)

    ## \return True when this image has uncompressed pixel data; False otherwise.
    @property
    def __has_pixels(self) -> bool:
        return (self.pixels is not None) and (len(self.pixels) > 0)

    ## Uses the uncompressed pixels (if present) to populate the exportable PIL image.
    ## Any existing exportable image, along with all its modifications, is discarded
    ## to create the new one.
    def create_exportable_image_from_pixels(self, image_mode: str = 'P'):
        # CREATE AN IMAGE ONLY IF THERE IS ENOUGH DATA PRESENT.
        if self.__is_valid:
            if not self.__has_expected_length:
                assert_equal(len(self.pixels), self.__expected_bitmap_length_in_bytes, 'pixels length in bytes', warn_only = True)
            self._exportable_image = Image.frombytes(image_mode, (self.width, self.height), self.pixels)
            if self._palette is not None:
                self._exportable_image.putpalette(self._palette.raw_rgb_bytes())
        else:
            # If there are no uncompressed pixels or insufficient dimensions,
            # an image cannot be constructed.
            self._exportable_image = None

    ## Exports the bitmap in the provided format to the provided filename.
    ## The bitmap can be exported in any format supported by Pillow.
    ## This method also supports two meta-formats:
    ##  - none: Do not export the image. Returns immediately.
    ##  - raw : Instead of exporting the decompressed and paletted image, 
    ##          only write the raw image data read from the file.
    ##          (for debugging/further reverse engineering)
    ## \param[in] root_directory_path - The directory where the animation frames and audio
    ##            should be exported.
    ## \param[in] command_line_arguments - All the command-line arguments provided to the 
    ##            script that invoked this function.
    def export(self, root_directory_path: str, command_line_arguments):
        if not self._include_in_export:
            return

        if hasattr(self, 'name') and self.name is not None:
            filename = os.path.join(root_directory_path, self.name)
        else:
            filename = root_directory_path

        if command_line_arguments.bitmap_format == 'none':
            return
        
        elif command_line_arguments.bitmap_format == 'raw':
            # WRITE THE RAW BYTES FROM THE FILE.
            if self.__has_raw_image_data:
                # Since the exported image data will not be openable by 
                # other programs, record some vital information (the 
                # dimensions) in the filename itself for later analysis.
                raw_filename = f'{filename}.{self.width}.{self.height}'
                with open(raw_filename, 'wb') as raw_file:
                    raw_file.write(self._raw)
            # If the image is not compressed, self.raw will have no data.
            # In this case, we want to write self.pixels instead.
            elif self.__has_pixels:
                with open(filename, 'wb') as pixels_file:
                    pixels_file.write(self.pixels)

        else:
            # WRITE A VIEWABLE BITMAP FILE WITH PILLOW.
            # The bitmap can be exported in any format supported by Pillow.
            if self._exportable_image is None:
                self.create_exportable_image_from_pixels()

            bitmap = self._exportable_image
            if bitmap is not None:
                # SAVE THE VIEWABLE BITMAP.
                filename_with_extension = f'{filename}.{command_line_arguments.bitmap_format}'
                bitmap.save(filename_with_extension, command_line_arguments.bitmap_format)
            elif self.__has_pixels:
                # WRITE THE RAW PIXELS.
                # This is a fallback in case there are pixels there but the bitmap cannot be created.
                # TODO: Warn here.
                with open(filename, 'wb') as pixels_file:
                    pixels_file.write(self.pixels)
            else:
                # CREATE AN EMPTY FILE.
                # TODO: Warn here.
                with open(filename, 'wb'):
                    pass
