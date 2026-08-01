# r15 large-file configure frontier

The r15 artifact reached Xash's real large-file configure probe after both
mandatory C and C++ link tests passed.

The pinned libdragon/newlib target reports a file-offset type smaller than
64 bits. Defining `_FILE_OFFSET_BITS=64` does not change that ABI. Xash's root
`wscript` already skips the same fatal probe for PSVita, which is documented in
the source as having no large-file support.

For the Uplink milestone, the complete PAK is 79,150,544 bytes. No selected
asset approaches the signed 32-bit offset ceiling, so r17 accepts the platform
limit and advances to source compilation.
