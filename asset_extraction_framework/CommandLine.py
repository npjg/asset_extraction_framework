import argparse
import logging
from typing import List

## Parses command-line arguments for an asset extraction script.
## \param[in] application_name - The name and version of the application from which assets
##            can be extracted. For example, "Tonka Construction (1997)". 
## \param[in] application_description - A description of the application under extraction, including
##            what versions, builds, and so forth are supported.
##            For example, "The first version of Tonka Construction. Currently on the Windows version is supported"
class CommandLineArguments:
  def __init__(self, application_name: str, application_description: str):
    self.argument_parser = argparse.ArgumentParser(
        formatter_class = argparse.RawTextHelpFormatter,
        description = (
          f'Extracts assets (text, sounds, bitmaps, animations) from {application_name} into a human-comprehensible structure.'
          f'\n\n{application_description}'))

    input_argument_help = f'Pass a filepath(s) to process the {application_name} file(s) in that path.'
    self.argument_parser.add_argument('input', nargs = '+', help = input_argument_help)

    export_argument_help = (
    'Specify the directory location for exporting assets, or omit to skip export.'
    '\n\n(If a directory that already exists is provided, a subdirectory with the name of the application will be created instead.)'
    f'\nIn the export directory, a JSON document ({application_name}.json) records the defined asset structure:'
    '\n- The plaintext fields in all file/asset objects will be written to this document.'
    '\n- For binary fields shorter than a given byte limit (default: 0x50 bytes), will be written as hex digits.'
    '\n  Any binary fields longer than this byte limit will be represented in JSON by a placeholder (default: <blob>)'
    '\n  (This partial binary field export can aid reverse-engineering unknown fields.)'
    '\n\nAny binary data (like images/sound) can also be exported:'
    '\n- When single asset will generate multiple files (for instance, an animation exported framewise),'
    '\n  the constituent files will be placed in a subdirectory named after the asset ID.'
    '\n- When a single asset will generate a single file (for instance, an animation exported to AVI), no directory is created.'
    '    Instead, the single file will be named after the asset ID.')
    self.argument_parser.add_argument('--export', nargs='?', default = None, help = export_argument_help)

    animation_format_argument_help = """Specify the desired export format for animations. 
    If 'none' is provided, animations will not exported.

    NOTE: Animation export is independent from export of constituent images/sounds:
    - Animation export can be disabled, but individual bitmap/sound export can still be enabled.
    - Animation export can be enabled, but individual bitmap/sound export can be disabled.
      (In this case, animation assets will only have one exported file.)"""
    self.argument_parser.add_argument('--animation-format', choices = ['avi', 'none'], default = 'none', help = animation_format_argument_help)

    bitmap_format_argument_help = """Specify the desired export format for bitmaps.
    If 'raw' is provided, no decompression or other transformation will occur on the original. Unless the bitmaps were stored uncompressed, expect unreadable output.
    If 'none' is provided, bitmaps will not exported."""
    self.argument_parser.add_argument('--bitmap-format', choices = ['bmp', 'raw', 'none'], default = 'bmp', help = bitmap_format_argument_help)

    audio_format_argument_help = """Specify the desired export format for audio.
    If 'raw' is provided, no decompression or other transformation will occur on the original. Unless the audio was stored uncompressed, expect unreadable output.
    If 'none' is provided, audio will not be exported."""
    self.argument_parser.add_argument('--audio-format', choices = ['wav', 'raw', 'none'], default = 'wav', help = audio_format_argument_help)

    bitmap_options_argument_help = """Specify at most one of these mutually-exclusive options for framing exported bitmaps and animations:
    no_framing: Export each bitmap exactly as it was read.
    animation_framing: If the bitmap belongs to an animation, frame it within the dimensions of the animation.
                        Otherwise, do not apply framing."""
    self.argument_parser.add_argument('--bitmap-options', choices = ['no_framing', 'animation_framing'], 
                                            default = 'no_framing', help = bitmap_options_argument_help)

    debug_argument_help = "Print verbose debugging information during parsing."
    self.argument_parser.add_argument("--debug", action = "store_true", default = False, help = debug_argument_help)

  # Gets the command-line arguments and acts on any global settings specified therein.
  def parse(self, raw_command_line: List[str] = None):
    # PARSE THE ARGUMENTS.
    # TODO: Specify the type here.
    arguments =  self.argument_parser.parse_args(raw_command_line)

    # SET THE GLOBAL DEBUG LEVEL.
    # This level should not change through the life of the application.
    # So we will just set it now so the client needn't worry about it.
    # The argument will still be present in the returned arguments,
    # so the client can do with it what it wants.
    if arguments.debug:
      logging.basicConfig(level = logging.DEBUG)
    else:
      logging.basicConfig(level = logging.WARNING)

    # RETURN THE PARSED ARGUMENTS.
    return arguments
  