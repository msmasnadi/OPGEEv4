'''
.. Created on: 2/12/15 as part of pygcam
   Imported into opgee on 3/29/21
   Common functions and data

.. Copyright (c) 2015-2021 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import pkgutil
import io
from .error import OpgeeException

DFLT_ENCODING = 'utf-8'

def getResource(relpath, decode=DFLT_ENCODING):
    """
    Extract a resource (e.g., file) from the given relative path in
    the opgee package.

    :param relpath: (str) a path relative to the opgee package
    :param decode: (str) the argument to use to decode the data, or
        None to return the data without decoding.
    :return: the file contents
    """
    contents = pkgutil.get_data('opgee', relpath)
    return contents.decode(decode) if decode else contents

def resourceStream(relpath, stream_type='text', decode=DFLT_ENCODING):
    """
    Return a stream on the resource found on the given path relative
    to the opgee package.

    :param relpath: (str) a path relative to the opgee package
    :param stream_type: (str) the type of stream to create, either 'text' or 'bytes'
    :return: (file-like stream) a file-like buffer opened on the desired resource.
    """
    valid_types = ('text', 'bytes')
    if stream_type not in valid_types:
        raise OpgeeException(f"resourceStream type argument {type} is not allowed; it must be one of {valid_types}")

    text = getResource(relpath, decode=decode)
    return io.BytesIO(text) if stream_type == 'bytes' else io.StringIO(text)

# Deprecated: probably not needed
# def copyResource(relpath, dest, overwrite=True):
#     """
#     Copy a resource from the 'opgee' package to the given destination.
#
#     :param relpath: (str) a path relative to the opgee package
#     :param dest: (str) the pathname of the file to create by copying the resource.
#     :param overwrite: (bool) if False, raise an error if the destination
#       file already exists.
#     :return: none
#     """
#     if not overwrite and os.path.lexists(dest):
#         raise OpgeeException(dest)
#
#     text = getResource(relpath)
#     with open(dest, 'w') as f:
#         f.write(text)
