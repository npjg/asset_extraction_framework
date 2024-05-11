`asset_extraction_framework` is a reverse-engineering framework for extracting multimedia assets from legacy software.

Unlike [`mrcrowbar`](https://github.com/moralrecordings/mrcrowbar) and other reverse-engineering packages, 
this library is not designed for editing data in-place. `asset_extraction_framework` instead focuses on extraction. 

You write the code that converts the data from your application into a standard format (pixels and PCM audio). 
`asset_extraction_frameworks` then provides the following:
 - A command-line extractor interface
 - Uses Pillow and ffmpeg to export images/audio in a wide variety of formats in various configurations.

For real-world examples, see my `asset_extraction_framework`-based projects:
 - [Media Station](https://github.com/npjg/MediaStation)
 - [Tonka](https://github.com/npjg/tonka)
 - ...and more coming soon!