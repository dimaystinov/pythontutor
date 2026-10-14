"""Container entrypoint. Never invoke with untrusted code on the host."""
import json
import os
import sys
import tempfile
from evaldontevil.execplainator import exec as trace_exec, simple_exec
from runner.images import InvalidImage, decode_image, read_output


def main():
    request = json.loads(sys.stdin.buffer.read(4 * 1024 * 1024 + 1))
    result = {'result': 'invalid_image', 'stdout': '', 'stderr': '', 'exception': None}
    with tempfile.TemporaryDirectory(prefix='job-') as directory:
        os.chdir(directory)
        try:
            if request.get('image') is not None:
                with open('input.png', 'wb') as stream:
                    stream.write(decode_image(request['image']))
            explain = request.get('explain') and request.get('image') is None
            result = (trace_exec if explain else simple_exec)(request['code'], request.get('stdin', ''))
            image = read_output(directory)
            if image is not None:
                result['image'] = image
        except InvalidImage as error:
            result.update(result='invalid_image', stderr=str(error), exception=None)
        finally:
            os.chdir('/tmp')
    sys.stdout.write(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    main()
