
import subprocess
import os
from typing import List, Optional
import wave
import numpy

from .Asset import Asset

## A section of contiguous audio data.
class Sound(Asset):
    def __init__(self):
        super().__init__()
        # This data probably needs to, at least, be uncompressed
        # before a waveform can be generated.
        self._raw: Optional[bytes] = None
        # Any custom decompressor outputs the PCM data here.
        # (Or any other data format that ffmpeg can process.)
        self._pcm: Optional[bytes] = None
        ## This defines the type of the audio storied. Will be passed to the
        ## wave library to write PCM audio out.
        ##
        ## The audio cannot be exported to a proper WAV without these options,
        ## but a 'raw' export will still work.
        ## True if the audio samples are signed; false otherwise.
        self._signed: Optional[bool] = True
        ## True if the audio samples are big-endian; false otherwise.
        self._big_endian: Optional[bool] = True
        ## The width of each sample, in bytes.
        self._sample_width: Optional[int] = None
        ## The bitrate must be specified in hertz. So, for instance,
        ## if the sample rate is 11.025 kHz, the sample rate provided
        ## here would be 11025.
        self._sample_rate: Optional[int] = None
        ## The number of channels in the audio.
        self._channel_count: Optional[int] = None
        ## This is the type of the audio stored. Will be passed to ffmpeg's -f option.
        ## If ffmpeg will be handling the audio conversion, this must be provided.
        ## Otherwise, this can be ignored.
        self._ffmpeg_audio_type: Optional[str] = None

    ## Exports the audio in the provided format to the provided filename.
    ## The audio can be exported in any format supported by ffmpeg.
    ## This method also has two meta-formats:
    ##  - none: Do not export the image. Returns immediately.
    ##  - raw : Instead of exporting the decompressed and paletted image, 
    ##          only write the raw image data read from the file.
    ##          (for debugging/further reverse engineering)
    ## \param[in] root_directory_path - The directory where the animation frames and audio
    ##            should be exported.
    ## \param[in] command_line_arguments - All the command-line arguments provided to the 
    ##            script that invoked this function.
    def export(self, root_directory_path: str, command_line_arguments):
        filepath_without_extension = os.path.join(root_directory_path, self.name)
        filepath_with_extension = f'{filepath_without_extension}.{command_line_arguments.audio_format}'
        if command_line_arguments.audio_format == 'none':
            # DO NOTHING.
            return
        elif command_line_arguments.audio_format == 'raw':
            # WRITE THE RAW BYTES FROM THE FILE.
            if self._raw is not None:
                with open(filepath_with_extension, 'wb') as raw_file:
                    raw_file.write(self._raw)
            # If the sound is not compressed, self.raw will have no data.
            # In this case, we want to write self.pcm directly instead.
            elif self._pcm is not None:
                with open(filepath_with_extension, 'wb') as pcm_file:
                    pcm_file.write(self._pcm)
        else:
            # WRITE A LISTENABLE FILE.
            if self._pcm is not None:
                if self._ffmpeg_audio_type:
                    self.convert_via_ffmpeg([self], filepath_with_extension)
                else:
                    self.convert_via_wave([self], filepath_with_extension)

    ## Writes an uncompressed WAV file using Python's built-in wave library.
    ## This is much faster than calling into ffmpeg, but only raw PCM can 
    ## be written with this method.
    ## \param[in] cls - 
    ## \param[in] audios - The list of sound chunks to convert.
    ## \param[in] filepath - The filepath of the exported audio file.
    @classmethod
    def convert_via_wave(cls, sounds: List['Sound'], filepath):
        # ENSURE THERE ARE SOUNDS TO EXPORT.
        # If ffmpeg is called with no sounds to export (like what happens with an animation
        # with no sound), an empty file will be created.
        if len(sounds) == 0:
            return

        # SET UP THE WAVE FILE.
        wave_file = wave.open(filepath, 'wb')
        wave_file.setnchannels(sounds[0]._channel_count)
        wave_file.setsampwidth(sounds[0]._sample_width)
        wave_file.setframerate(sounds[0]._sample_rate)

        # WRITE THE AUDIO FRAMES.
        for sound in sounds:
            if (sound is not None) and (sound._pcm is not None):
                wave_file.writeframes(sound._pcm)

    ## Writes an audio file by calling into ffmpeg.
    ## This is significantly slower than writing a WAV file with the built-in wave library,
    ## but audio can be written in other formats than raw PCM.
    ## \param[in] cls - 
    ## \param[in] audios - The list of sound chunks to convert.
    ## \param[in] filepath - The filepath of the exported audio file.
    @classmethod
    def convert_via_ffmpeg(cls, sounds: List['Sound'], filepath):
        # ENSURE THERE ARE SOUNDS TO EXPORT.
        # If ffmpeg is called with no sounds to export (like what happens with an animation
        # with no sound), an empty file will be created.
        if len(sounds) == 0:
            return 

        # ASK FFMPEG TO WRITE LISTENABLE FILE.
        # The audio can be exported in any format supported by ffmpeg.
        # The raw audio is piped to ffmpeg.
        audio_conversion_command = ['ffmpeg', \
            # Any existing file should be overwritten without prompting.
            '-y', \
            # Because we are piping raw audio, we must provide a format.
            '-f', sounds[0].audio_type, \
            '-ar', sounds[0]._sample_rate, \
            # The channel count is stored as an integer, but we must convert to a string.
            '-ac', str(sounds[0]._channel_count), \
            # The input file is a pipe.
            '-i', 'pipe:', \
            # The output is the given file.
            filepath]
        with subprocess.Popen(audio_conversion_command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) as ffmpeg:
            for sound in sounds:
                if sound._pcm is not None:
                    ffmpeg.stdin.write(sound._pcm)
            ffmpeg.communicate()
