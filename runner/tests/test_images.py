import base64
import io
import os
import struct
import zlib

import pytest
from PIL import Image
from runner.images import InvalidImage, decode_image, normalize_image, read_output, MAX_IMAGE_BYTES
from runner.server import execute


def picture(format='PNG', size=(8, 6)):
    stream = io.BytesIO()
    Image.new('RGB', size, (250, 40, 10)).save(stream, format=format)
    return stream.getvalue()


def test_image_input_conversion():
    for format in ('PNG', 'JPEG'):
        raw = picture(format)
        normalized = decode_image(base64.b64encode(raw).decode())
        assert normalized.startswith(b'\x89PNG')
        assert Image.open(io.BytesIO(normalized)).size == (8, 6)


def test_invalid_and_oversized_images():
    for raw in (b'not image', b'x' * (MAX_IMAGE_BYTES+1)):
        with pytest.raises(InvalidImage):
            normalize_image(raw)
    with pytest.raises(InvalidImage):
        decode_image('data:image/png;base64,AAAA')
    with pytest.raises(InvalidImage):
        normalize_image(picture(size=(2001, 2000)))
    # A tiny PNG claiming enormous dimensions must be rejected before allocation.
    raw = picture()
    ihdr = struct.pack('>IIBBBBB', 100000, 100000, 8, 2, 0, 0, 0)
    bomb = raw[:8] + struct.pack('>I', 13) + b'IHDR' + ihdr + struct.pack('>I', zlib.crc32(b'IHDR'+ihdr)) + raw[33:]
    with pytest.raises(InvalidImage):
        normalize_image(bomb)


def test_output_file_policy(tmp_path):
    assert read_output(tmp_path) is None
    file = tmp_path/'output.png'
    file.write_bytes(picture())
    assert decode_image(read_output(tmp_path)).startswith(b'\x89PNG')
    file.unlink()
    file.symlink_to('/etc/passwd')
    with pytest.raises(InvalidImage):
        read_output(tmp_path)
    file.unlink()
    file.mkdir()
    with pytest.raises(InvalidImage):
        read_output(tmp_path)
    file.rmdir()
    os.mkfifo(file)
    with pytest.raises(InvalidImage):
        read_output(tmp_path)


@pytest.mark.skipif(os.getenv('RUN_DOCKER_TESTS') != '1', reason='Requires built Python 3.14 worker')
def test_real_opencv_image_job():
    source = '''import sys, cv2, numpy as np
print(sys.version.split()[0])
print(cv2.__version__, np.__version__)
image = cv2.imread('input.png')
cv2.imwrite('output.png', cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
print(image.shape)
'''
    result = execute({'code': source, 'stdin':'', 'explain': False,
                      'image': base64.b64encode(picture('JPEG')).decode()})
    assert result['result'] == 'ok', result
    assert result['stdout'].startswith('3.14.7\n5.0.0 2.5.3\n')
    assert Image.open(io.BytesIO(decode_image(result['image']))).size == (8,6)
    for code in ["import os; os.symlink('/etc/passwd','output.png')", "open('output.png','w').write('bad')"]:
        result = execute({'code':code, 'stdin':'', 'explain':False})
        assert result['result'] == 'invalid_image', result
    # Reject a forged output payload outside the learner process too.
    code = "import os,json; os.write(1,json.dumps({'result':'ok','stdout':'','stderr':'','exception':None,'image':'AAAA'}).encode()); os._exit(0)"
    assert execute({'code':code, 'stdin':'', 'explain':False})['result'] == 'invalid_image'
