import subprocess
import os
from typing import Optional

from .Asset import Asset

## A snippet of audio data.
class Sound(Asset):
    def __init__(self):
        super().__init__()

        # DEFINE A FIELD FOR RAW DATA FROM THE FILE.
        # This data probably needs to, at least, be uncompressed
        # before a waveform can be generated.
        self.raw: Optional[bytes] = None

        # DEFINE A FIELD FOR THE WAVEFORM (USUALLY PCM).
        # Any custom decompressor outputs the PCM data here.
        # (Or any other data format that ffmpeg can process.)
        self.pcm: Optional[bytes] = None

        # DEFINE FIELDS FOR REQUIRED AUDIO METADATA.
        # The audio cannot be exported to a proper WAV without these options,
        # but a 'raw' export will still work. If the audio type and bitrate
        # are provided, they must be provided in a form that ffmpeg can read.
        # For example, 
        self.audio_type: Optional[str] = None
        self.bitrate: Optional[str] = None
        self.channel_count: Optional[int] = None

    ## Exports the audio in the provided format to the provided filename.
    ## The audio can be exported in any format supported by ffmpeg.
    ## This method also has two meta-formats:
    ##  - none: Do not export the image. Returns immediately.
    ##  - raw : Instead of exporting the decompressed and paletted image, 
    ##          only write the raw image data read from the file.
    ##          (for debugging/further reverse engineering)
    ## \param[in] filename_without_extension - The full filepath of the desired export
    ##            except the extension. The extension wil be added based on the requested
    ##            export format.
    ## \param[in] command_line_arguments - All the command-line arguments provided to the 
    ##            script that invoked this function.
    def export(self, filename_without_extension: str, command_line_arguments):
        if command_line_arguments.audio_format == 'none':
            # DO NOTHING.
            return
        elif command_line_arguments.audio_format == 'raw':
            # WRITE THE RAW BYTES FROM THE FILE.
            raw_filepath = f'{filename_without_extension}.raw_sound'
            if self.raw is not None:
                with open(raw_filepath, 'wb') as raw_file:
                    raw_file.write(self.raw)
            # If the sound is not compressed, self.raw will have no data.
            # In this case, we want to write self.pcm directly instead.
            elif self.pcm is not None:
                with open(raw_filepath, 'wb') as pcm_file:
                    pcm_file.write(self.pcm)
        else:
            # ASK FFMPEG TO WRITE LISTENABLE FILE.
            # The audio can be exported in any format supported by ffmpeg.
            # The raw audio is piped to ffmpeg.
            filename_with_extension = f'{filename_without_extension}.{command_line_arguments.audio_format}'
            if self.pcm is not None:
                audio_conversion_command = ['ffmpeg', \
                    # Any existing file should be overwritten without prompting.
                    '-y', \
                    # Because we are piping raw audio, we must provide a format.
                    '-f', self.audio_type, \
                    '-ar', self.bitrate, \
                    # The channel count is stored as an integer, but we must convert to a string.
                    '-ac', str(self.channel_count), \
                    # The input file is a pipe.
                    '-i', 'pipe:', \
                    # The output is the given file.
                    filename_with_extension]
                with subprocess.Popen(audio_conversion_command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) as ffmpeg:
                    ffmpeg.communicate(input = self.pcm)
