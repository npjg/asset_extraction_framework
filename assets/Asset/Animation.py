
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
        
        # DEFINE REQUIRED ANIMATION METADATA FIELDS.
        # The animation cannot be exported without these required properties.
        # The width and height are expressed in pixels.
        self._width: Optional[int] = None
        self._height: Optional[int] = None

        # DEFINE ANIMATION COORDINATES.
        # WIthout these, the animation can only be exported standalone.
        # If frames have coordinates defined absolutely, these must be provided.
        self._left: Optional[int] = None
        self._top: Optional[int] = None
        self._right: Optional[int] = None
        self._bottom: Optional[int] = None

        # DEFINE THE ALPHA COLOR.
        # This is the color (or color index) to use when reframing individual bitmaps 
        # to have the same dimensions as the overall animation.
        self.alpha_color: int = 0xff

        # DEFINE PLAYBACK RATES.
        # Currently, only constant-framerate animations are supported. The framerate is specified
        # in frames per second.
        # TODO: Framerate is not currently used for export.
        self.framerate: Optional[float] = None
        # Many games encode animations as a series of frames followed by a constant-duration
        # audio stream, so rather than explicitly providing a framerate, the number of frames per
        # audio stream can be provided so the framerate can be calculated implicitly.
        self.bitmaps_per_audio: Optional[int] = None

        # DEFINE WHERE TO HOLD ANIMATION FRAMES AND AUDIO.
        # Any animation class that inherits from this one should store
        # its frames and audio here.
        self.bitmaps: List[RectangularBitmap] = []
        self.audios: List[Sound] = []

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

    ## \return The nominal bounding box (as claimed by the frames' coordinates.
    ## This is not guaranteed to be the minimal bounding box or 
    ## even contain all frames of the animation at all. To calculate
    ## the minimal bounding box, use the minimal_bounding_box method.
    @property
    def bounding_box(self) -> BoundingBox:
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
    def minimal_bounding_box(self) -> BoundingBox:
        # MAKE SURE FRAMES ARE PRESENT.
        # If there are not frames present, the calls further on will error out
        # because the will be fed empty lists.
        no_frames_present: bool = (len(self.bitmaps) == 0)
        if no_frames_present:
            return

        # GET ALL THE BOUNDING BOXES IN THE ANIMATION.
        frame_bounding_boxes: List[BoundingBox] = []
        for frame in self.bitmaps:
            bounding_box: bool = frame.bounding_box
            if bounding_box is not None:
                frame_bounding_boxes.append(bounding_box)
        # DO NOT CONTINUE IF THERE ARE NO BOUNDING BOXES.
        if len(frame_bounding_boxes) == 0:
            return

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
        return BoundingBox(minimal_top, minimal_left, minimal_bottom, minimal_right)

    ## \return True if this animation has at least one audio chunk; False otherwise.
    @property
    def has_audio(self) -> bool:
        return len(self.audios) > 0

    ## Exports this animation to a set of images/audio files or a single animation file.
    ## \param[in] root_directory_path - The directory where the animation frames and audio
    ##            should be exported.
    ## \param[in] command_line_arguments - All the command-line arguments provided to the 
    ##            script that invoked this function.
    def export(self, root_directory_path: str, command_line_arguments):
        # CREATE THE DIRECTORY FOR THE EXPORTED ASSET.
        export_animation_as_one_file = command_line_arguments.animation_format != 'none'
        if export_animation_as_one_file:
            # Create a temporary directory for the individual images and audios.
            frame_export_directory_path = tempfile.mkdtemp()
        else:
            # A directory is only needed if the asset has more 
            # than one associated file (like an animation with 
            # multiple image bitmap frames).
            frame_export_directory_path = os.path.join(root_directory_path, self.name)
            Path(frame_export_directory_path).mkdir(parents = True, exist_ok = True)

        # EXPORT INDIVIDUAL BITMAPS ACCORDING TO THEIR SETTINGS.
        # The export directory will contain files like the following:
        #  - 0.bmp
        #  - 1.bmp
        #    ...
        #  Up to the number of bitmaps in this animation.
        for index, frame in enumerate(self.bitmaps):
            export_filepath = os.path.join(frame_export_directory_path, f'{index}')
            # DETERMINE WHETHER TO REFRAHE THIS BITMAP.
            # If we want to export a single animation file, (animation format is not 'none'), 
            # this image must be resized (reframed) to the full size of the animation.
            # This ensures all bitmaps in the exported animation have the same dimensions.
            # The exported animation would look kooky otherwise. The user can also request
            # this reframing for frame-wise exports.
            apply_animation_framing: bool = (command_line_arguments.bitmap_options == 'animation_framing') or \
                (command_line_arguments.animation_format != 'none')
            if apply_animation_framing:
                # RESIZE THIS BITMAP TO THE FULL ANIMATION SIZE.
                # Reframing the bitmap implies there are uncompressed pixels available.
                # It would not make sense to resize unproccessed pixels, becuase we cannot
                # understand them.
                reframed_animation: Image = self._reframe_to_animation_size(frame)
                if reframed_animation is not None:
                    # Because we are working with a PIL Image now, we will just export it directly.
                    # No need to add complexity by creating the indirection of a dummy RectangularBitmap object.
                    export_filepath_with_extension = f'{export_filepath}.{command_line_arguments.bitmap_format}'
                    reframed_animation.save(
                        export_filepath_with_extension, command_line_arguments.bitmap_format)
            else:
                # EXPORT THE BITMAP AS IS.
                frame.export(export_filepath, command_line_arguments)

        # EXPORT INDIVIDUAL SOUNDS ACCORDING TO THEIR SETTINGS.
        # The export directory will contain files like the following:
        #  - 0.wav
        #  - 1.wav
        #    ...
        # Up to the number of audio chunks in the animation.
        # (Because many games show many frames while playing one sound chunk, the number of 
        #  audio chunks will probably be much less than the number of frames.)
        for index, audio in enumerate(self.audios):
            if audio.name is None:
                audio.name = f'{index}'
            export_filepath = os.path.join(frame_export_directory_path, f'{index}')
            audio.export(export_filepath, command_line_arguments)

        # IF REQUESTED, EXPORT THE ANIMATION AS A SINGLE FILE.
        if export_animation_as_one_file:
            # LIST ALL THE ANIMATION BITMAP FILEPATHS.
            # For bitmaps, ffmpeg supports format string notation.
            # The format string %d.bmp will specify the bitmaps
            # in directory order.
            animation_bitmaps_set = os.path.join(frame_export_directory_path, f'%d.{command_line_arguments.bitmap_format}')

            # LIST ALL THE ANIMATION SOUND FILEPATHS.
            # Because ffmpeg does not support the %d syntax for audio, 
            # write a temporary file that enumerates all the audio files.
            audio_set_text_filepath = os.path.join(frame_export_directory_path, 'audios.txt')
            with open(audio_set_text_filepath, 'w') as audio_set_text_file:
                for index, audio in enumerate(self.audios):
                    audio_export_filepath = os.path.join(frame_export_directory_path, f'{audio.name}.{command_line_arguments.audio_format}')
                    audio_set_text_file.write(f'file {audio_export_filepath}\n')
            # The conversion command must include some extra options.
            audio_conversion_command = ['-safe', '0', 
                '-f', 'concat', 
                '-i', audio_set_text_filepath, 
                '-c', 'copy']

            # RUN THE CONVERSION THROUGH FFMPEG.
            # The individual frames were exported to a temporary directory,
            # but the animation should be exported to the requested export 
            # directory provided by the user.
            animation_filepath = os.path.join(root_directory_path, f'{self.name}.{command_line_arguments.animation_format}')
            animation_conversion_command = ['ffmpeg', '-y', \
                '-r', f'{self.bitmaps_per_audio}', \
                # First, we specify the set of bitmaps.
                '-i', animation_bitmaps_set, \
                # Then, we specify the set of audio files.
                *audio_conversion_command,
                # Lossless compression should be applied.
                '-vcodec', 'libx264', \
                '-crf', '0', \
                animation_filepath]
            # Invoke ffmpeg to combine the video and audio together
            # into a single animation file.
            with subprocess.Popen(
                    animation_conversion_command, 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.STDOUT) as ffmpeg:
                ffmpeg.communicate()

    ## Places an animation frame bitmap on a canvas the size of the entire 
    ## animation. Thus, each frame image will have the same dimensions.
    ## \return The reframed animation frame bitmap if it exists, None otherwise.
    ## \param[in] bitmap - The rectangular bitmap whose image should be reframed.
    def _reframe_to_animation_size(self, bitmap: RectangularBitmap) -> Optional[Image.Image]:
        # GET THE IMAGE.
        image: Image = bitmap.bitmap
        if image is None:
            return None

        # CREATE THE FULL-SIZED FRAME TO HOLD THE ANIMATION IMAGE.
        # The full frame must be filled with the alpha color used throughout the game.
        full_frame_dimensions = (self.minimal_bounding_box.width, self.minimal_bounding_box.height)
        full_frame = Image.new('P', full_frame_dimensions, color = self.alpha_color)
        if bitmap.palette:
            # APPLY THE ORIGINAL PALETTE TO THIS ONE.
            full_frame.putpalette(bitmap.palette.rgb_colors)

        # PASTE THE ANIMATION FRAME IN THE APPROPRIATE PLACE.
        image_location = (bitmap.left - self.minimal_bounding_box.left, bitmap.top - self.minimal_bounding_box.top)
        full_frame.paste(image, box = image_location)
        return full_frame
        