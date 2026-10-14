"""Bounded image decoding shared by worker and trusted control plane."""
import base64
import binascii
import io
import os
import stat
import warnings
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BASE64 = 4 * ((MAX_IMAGE_BYTES + 2) // 3)
MAX_IMAGE_PIXELS = 4_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

class InvalidImage(ValueError):
    pass


def normalize_image(raw):
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise InvalidImage('Image must contain at most 2 MiB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw), formats=('PNG', 'JPEG')) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise InvalidImage('Image must contain at most 4 million pixels.')
                image.load()
                # Copy only pixels: discard EXIF, text, profiles and ancillary chunks.
                pixels = image.convert('RGB')
                clean = Image.new('RGB', pixels.size)
                clean.paste(pixels)
                output = io.BytesIO()
                clean.save(output, format='PNG')
                data = output.getvalue()
                if len(data) > MAX_IMAGE_BYTES:
                    raise InvalidImage('Normalized image exceeds 2 MiB.')
                return data
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        if isinstance(error, InvalidImage):
            raise
        raise InvalidImage('Invalid PNG or JPEG image.') from error


def decode_image(encoded):
    if not isinstance(encoded, str) or len(encoded) > MAX_IMAGE_BASE64:
        raise InvalidImage('Image must be base64, at most 2 MiB decoded.')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise InvalidImage('Invalid base64 image.') from error
    return normalize_image(raw)


def encode_image(raw):
    return base64.b64encode(raw).decode('ascii')


def read_output(directory):
    try:
        fd = os.open(os.path.join(directory, 'output.png'), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise InvalidImage('output.png must be a regular image file, not a link.') from error
    status = os.fstat(fd)
    if not stat.S_ISREG(status.st_mode) or status.st_size > MAX_IMAGE_BYTES:
        os.close(fd)
        raise InvalidImage('output.png must be a regular file of at most 2 MiB.')
    with os.fdopen(fd, 'rb') as stream:
        return encode_image(normalize_image(stream.read(MAX_IMAGE_BYTES + 1)))
