
from typing import List, Optional
import os
import subprocess
from pathlib import Path
import tempfile

from PIL import Image

from .Asset import Asset
from .BoundingBox import BoundingBox
from .Image import RectangularBitmap
from .Sound import Sound

## Defines an an animation as a series of rectangular bitmaps (frames)
## that display at a given framerate and are optionally 
## accompanied by audio.
class Animation(Asset):
    ## Parses the animation.
    def __init__(self):
        super().__init__()
        # The animation cannot be exported without these required properties.
        # The width and height are expressed in pixels.
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        self.__minimal_bounding_box = None
        self.__animation_framing_applied: bool = False
        # WIthout these, the animation can only be exported standalone.
        # If frames have coordinates defined absolutely, these must be provided.
        self._left: Optional[int] = None
        self._top: Optional[int] = None
        self._right: Optional[int] = None
        self._bottom: Optional[int] = None
        # This is the color (or color index) to use when reframing individual bitmaps 
        # to have the same dimensions as the overall animation.
        self._alpha_color: int = 0xff
        # Currently, only constant-framerate animations are supported. The framerate is specified
        # in frames per second.
        # TODO: Framerate is not currently used for export.
        self._framerate: Optional[float] = None
        # Many games encode animations as a series of frames followed by a constant-duration
        # audio stream, so rather than explicitly providing a framerate, the number of frames per
        # audio stream can be provided so the framerate can be calculated implicitly.
        self._bitmaps_per_audio: Optional[int] = None
        # Any animation class that inherits from this one should store
        # its frames and audio here.
        self._keyframes: List[RectangularBitmap] = []
        self.frames: List[RectangularBitmap] = []
        self.sounds: List[Sound] = []

    ## \return The nominal width of the animation.
    ## Does not do any calculation on the frames; instead relies on the 
    ## coordinates for the animation itself. Thus, this might not exist
    ## or might not be the "minimal" dimension that encloses all the frames.
    @property
    def width(self) -> Optional[int]:
        if self._width is not None:
            # GET THE NOMINAL WIDTH.
            return self._width
        elif (self._left is not None) and (self._right is not None):
            # CALCULATE THE NOMINAL WIDTH FROM COORDINATES.
            return self._right - self._left
        else:
            # RETURN NOTHING.
            # There is not enough information to calculate the nominal width.
            return None

    ## \return The nominal height of the animation.
    ## Does not do any calculation on the frames; instead relies on the 
    ## coordinates for the animation itself. Thus, this might not exist
    ## or might not be the "minimal" dimension that encloses all the frames.
    @property
    def height(self) -> Optional[int]:
        if self._height is not None:
            # GET THE NOMINAL HEIGHT.
            return self._height
        elif (self._top is not None) and (self._bottom is not None):
            # CALCULATE THE HEIGHT FROM COORDINATES.
            return self._bottom - self._top
        else:
            # RETURN NOTHING.
            # There is not enough information to calculate the height.
            return None

    ## \return The nominal top rectangular coordinate of the bitmap.
    ## Rectangle coordinates are generally defined as the following:
    ##  - left coordinate
    ##  - top coordinate
    ##  - width
    ##  - height
    ## Because of this convention, there should be no need to calculate
    ## this coordinate from other coordinates.
    ##
    ## This property is included to provide a consistent interface with 
    ## other coordinates that can be calculated.
    @property
    def top(self) -> Optional[int]:
        return self._top

    ## \return The nominal left rectangular coordinate of the animation.
    ## There should be no need to calculate this coordinate from other coordinates.
    ##
    ## This property is included to provide a consistent interface with 
    ## other coordinates that can be calculated.
    @property
    def left(self) -> Optional[int]:
        return self._left

    ## \return The nominal right rectangular coordinate of the animation.
    ## Because of the convention noted above, this coordinate can be calculated
    ## from other coordinates, if they are provided.
    @property
    def right(self) -> Optional[int]:
        if self._right is not None:
            # GET THE NOMINAL RIGHT COORDINATE.
            return self._right
        elif (self._left is not None) and (self._width is not None):
            # CALCULATE THE COORDINATE.
            return self._left + self._width
        else:
            # RETURN NOTHING.
            # There is not enough information to calculate this coordinate.
            return None

    ## \return The nominal bottom rectangular coordinate of the bitmap.
    ## Because of the convention noted above, this coordinate can be calculated
    ## from other coordinates, if they are provided.
    @property 
    def bottom(self)  -> Optional[int]:
        if self._bottom is not None:
            # GET THE NOMINAL BOTTOM COORDINATE.
            return self._bottom
        elif (self._top is not None) and (self._height is not None):
            # CALCULATE THE COORDINATE.
            return self._top + self._height
        else:
            # RETURN NOTHING.
            # There is not enough information to calculate this coordinate.
            return None

    ## \return The nominal bounding box (as claimed by the frames' coordinates).
    ## This is not guaranteed to be the minimal bounding box or 
    ## even contain all frames of the animation at all. To calculate
    ## the minimal bounding box, use the minimal_bounding_box method.
    @property
    def _bounding_box(self) -> BoundingBox:
        # Note that this bounding box might not be the true bounding box the animation, 
        # as would be calculated from the actual dimensions of the frames in the animation.
        return BoundingBox(self.top, self.left, self.bottom, self.right)

    ## \return The bounding box that encloses all the frames (bitmaps) in the animation.
    ## If the bounding boxes for all the frames are minimal (usually true), this will also be 
    ## the minimal bounding box for the animation.
    ##
    ## When a game provides inaccurate nominal animation bounding boxes, this property
    ## might return better results at the expense of a bit more calculation.
    @property
    def _minimal_bounding_box(self) -> BoundingBox:
        # RETURN THE CACHED BOUNDING BOX.
        if self.__minimal_bounding_box is not None: 
            return self.__minimal_bounding_box

        # MAKE SURE FRAMES ARE PRESENT.
        # If there are not frames present, the calls further on will error out
        # because the will be fed empty lists.
        no_frames_present: bool = (len(self.frames) == 0)
        if no_frames_present:
            return

        # GET ALL THE BOUNDING BOXES IN THE ANIMATION.
        frame_bounding_boxes: List[BoundingBox] = []
        for frame in self.frames:
            bounding_box: bool = frame._bounding_box
            if bounding_box is not None:
                frame_bounding_boxes.append(bounding_box)
        if len(frame_bounding_boxes) == 0:
            return None

        # FIND THE SMALLEST RECTANGLE THAT CONTAINS ALL THE FRAME BOUNDING BOXES.
        # This smallest rectangle will have the following vertices:
        #  - Left: The left vertex of the leftmost bounding box.
        #  - Top: The top vertex of the topmost bounding box.
        #  - Right: The right vertex of the rightmost bounding box.
        #  - Bottom: The bottom vertext of the bottommost bounding box.
        minimal_left: int = min([bounding_box.left for bounding_box in frame_bounding_boxes])
        minimal_top: int = min([bounding_box.top for bounding_box in frame_bounding_boxes])
        minimal_right: int = max([bounding_box.right for bounding_box in frame_bounding_boxes])
        minimal_bottom: int = max([bounding_box.bottom for bounding_box in frame_bounding_boxes])
        self.__minimal_bounding_box = BoundingBox(minimal_top, minimal_left, minimal_bottom, minimal_right)
        return self.__minimal_bounding_box

    ## \return True if this animation has at least one audio chunk; False otherwise.
    @property
    def __has_audio(self) -> bool:
        return len(self.sounds) > 0

    ## \return True if this animation has at least one frame; False otherwise.
    @property
    def __has_frames(self) -> bool:
        return len(self.frames) > 0

    ## \return True if this animation has only audio and no bitmaps; False otherwise.
    @property
    def __has_audio_only(self) -> bool:
        return (self.__has_audio) and (not self.__has_frames)

    ## \return True if this animation has only bitmaps and no audio; False otherwise.
    @property
    def __has_frames_only(self) -> bool:
        return (self.__has_frames) and (not self.__has_audio)

    ## \return A single Sound object that has all the sounds from this
    ## animation concatenated into one PCM stream.
    ## None if there are no sounds in this animation.
    @property
    def sound(self) -> Sound:
        pass

    ## Exports this animation to a set of images/audio files or a single animation file.
    ## \param[in] root_directory_path - The directory where the animation frames and audio
    ##            should be exported.
    ## \param[in] export_sounds_individually - If True, write each entry in self.audios
    ##            to a separate file. Otherwise, create one audio file that is a simple
    ##            concatenation of the entries in self.audios.
    ## \param[in] command_line_arguments - All the command-line arguments provided to the 
    ##            script that invoked this function.
    def export(self, root_directory_path: str, command_line_arguments):
        # DETERMINE WHERE EXPORTED FRAMES/AUDIO SHOULD BE STORED.
        if self.__has_audio_only:
            # DO NOT CREATE A SUBDIRECTORY FOR THIS ANIMATION.
            # A directory is only needed if the asset will create more
            # than one exported file. 
            # 
            # There are two ways an animation can generate only one exported file:
            #  - The animation is all audio and export_sounds_individually is False.
            #  - The animation contains only one bitmap frame and no audio.
            frame_export_directory_path = root_directory_path
        else:
            # CREATE A SUBDIRECTORY.
            frame_export_directory_path = os.path.join(root_directory_path, self.name)
            Path(frame_export_directory_path).mkdir(parents = True, exist_ok = True)    

        # EXPORT INDIVIDUAL BITMAPS ACCORDING TO THEIR SETTINGS.
        # The export directory will contain files like the following:
        #  - 0.bmp
        #  - 1.bmp
        #    ...
        #  Up to the number of bitmaps in this animation.
        self._reframe_to_animation_size(command_line_arguments)
        for index, frame in enumerate(self.frames):
            export_filepath = os.path.join(frame_export_directory_path, f'{index}')
            frame.export(export_filepath, command_line_arguments)

        # EXPORT INDIVIDUAL SOUNDS ACCORDING TO THEIR SETTINGS.
        # The export directory will contain files like the following:
        #  - 0.wav
        #  - 1.wav
        #    ...
        # Up to the number of audio chunks in the animation.
        # (Because many games show many frames while playing one sound chunk, the number of 
        #  audio chunks will probably be much less than the number of frames.)
        if len(self.sounds) > 0:
            Sound.convert_via_wave(self.sounds, f'{frame_export_directory_path}/audio.{command_line_arguments.audio_format}')

    ## Places an animation frame bitmap on a canvas the size of the entire 
    ## animation. Thus, each frame image will have the same dimensions.
    ## \return The reframed animation frame bitmap if it exists, None otherwise.
    ## \param[in] bitmap - The rectangular bitmap whose image should be reframed.
    def _reframe_to_animation_size(self, command_line_arguments):
        # DETERMINE WHETHER TO REFRAHE THIS BITMAP.
        # If we want to export a single animation file, (animation format is not 'none'), 
        # this image must be resized (reframed) to the full size of the animation.
        # This ensures all bitmaps in the exported animation have the same dimensions.
        # The exported animation would look kooky otherwise. The user can also request
        # this reframing for frame-wise exports.
        apply_animation_framing: bool = (command_line_arguments.bitmap_options == 'animation_framing') or \
            (command_line_arguments.animation_format != 'none')
        if not apply_animation_framing or (self.__animation_framing_applied == True):
            # RESIZE THIS BITMAP TO THE FULL ANIMATION SIZE.
            # Reframing the bitmap implies there are uncompressed pixels available.
            # It would not make sense to resize unproccessed pixels, becuase we cannot
            # understand them.
            return

        bounding_box = self._minimal_bounding_box
        for frame in self.frames:
            bitmap: Image = frame._exportable_image
            if bitmap is None:
                frame.create_exportable_image_from_pixels()
                bitmap = frame._exportable_image
                if bitmap is None:
                    continue

            # CREATE THE FULL-SIZED FRAME TO HOLD THE ANIMATION IMAGE.
            # The full frame must be filled with the alpha color used throughout the game.
            MAXIMUM_ANIMATION_WIDTH = 5000
            MAXIMUM_ANIMATION_HEIGHT = 5000
            frame_exceeds_max_width = bounding_box.width > MAXIMUM_ANIMATION_WIDTH
            frame_exceeds_max_height = bounding_box.height > MAXIMUM_ANIMATION_HEIGHT
            if frame_exceeds_max_width or frame_exceeds_max_height:
                continue
            full_frame_dimensions = (bounding_box.width, bounding_box.height)
            full_frame = Image.new('P', full_frame_dimensions, color = self._alpha_color)
            if frame._palette is not None:
                # full_frame.palette = bitmap.palette
                full_frame.putpalette(frame._palette.raw_rgb_bytes())

            # PASTE THE ANIMATION FRAME IN THE APPROPRIATE PLACE.
            bitmap_left_top_with_respect_to_animation = (frame.left - bounding_box.left, frame.top - bounding_box.top)
            full_frame.paste(bitmap, box = bitmap_left_top_with_respect_to_animation)
            frame._exportable_image = full_frame
        # Applying the framing or checking if it has been applied is pretty costly,
        # so a flag will be set instead to make sure it is not done twice. This can 
        # happen if, for instance, client code needs to apply keyframes and thus needs
        # the animation framing to be applied first.
        self.__animation_framing_applied = True