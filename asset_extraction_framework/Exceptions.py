from hexdump2 import hexdump

class BinaryParsingError(Exception):
    """
    Displays a descriptive hexdump, with a variable amount of context, to accompany an exception
    when reading/parsing binary streams. Because the current position of the stream is used 
    to determine the data that is shown, this is really only useful for errors that happen
    while or immediately after reading some data from a stream.

    Args:
        message (str): A typical exception message, nothing special here.
        stream (object): The binary stream. Must support the tell, seek, and read methods.
            If a stream is not provided, no hexdump will be appended to the exception message.
        context_length_before (int): The number of bytes of context to show in the hexdump
            before the current stream position.
        context_length_after (int): The number of bytes of context to show in the hexdump
            after the current stream position.

    Example:
        Here is an example exception message: 
        nefile.Exceptions.BinaryParsingError: BitmapInfoHeader doesn't have expected length.

        Position: 0x6e14
        Context:
        00006df4  00 00 00 00 00 00 00 00  62 5b 01 00 02 00 50 05  |........b[....P.|
        00006e04  ff 00 07 00 6d 74 73 77  73 6c 6e 6b 01 01 2d 00  |....mtswslnk..-.|
        00006e14  24 00 40 00 40 00 08 00  00 00 ff ff ff ff ff ff  |$.@.@...........|
        00006e24  ff ff 80 00 00 00 00 00  00 01 80 00 00 00 00 00  |................|
        00006e34  00                                                |.|
        00006e35
    """
    def __init__(self, message, stream=None, context_length_before=0x20, context_length_after=0x20):
        if stream is not None:
            original_stream_position = stream.tell()
            context_start_pointer = stream.tell() - context_length_before
            stream.seek(context_start_pointer)
            total_bytes_to_read = context_length_before + 1 + context_length_after
            data_to_dump = stream.read(total_bytes_to_read)
            stream.seek(original_stream_position)
            dump_string = hexdump(data_to_dump, result = 'return', offset = context_start_pointer, collapse = True)
            message = f'{message}\n\nPosition: 0x{stream.tell():04x}\nContext:\n{dump_string}'
            
        super().__init__(message)
