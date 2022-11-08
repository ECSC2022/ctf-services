import re
import os
import os
import io
import stat
import json
import tarfile
from base64 import b64encode as b64e, b64decode as b64d
from http.cookies import SimpleCookie

from js import window, console, alert, URL, document, localStorage, Blob
from pyodide.ffi import create_proxy, to_js


# constants
COOKIE_NAME = '_unpacked_dict-v1'
STDOUT = 'out'
UPLOAD_BTN_ID = 'upload'
DOWNLOAD_COL_ID = 'col-download'
PORTABLE_BTN_ID = 'portable'
PORTABLE_COL_ID = 'col-portable'
TREE_DIV_NODE = 'tree'
TEXT_EXTS = ['txt', 'md']
IMAGE_EXTS = ['png', 'jpeg', 'gif', 'jpg']

# global vars
uploaded_dict = dict()
unpacked_dict = dict()


class Archive:
    """Abstraction for archives."""

    def __init__(self, fname, blob):
        self.fname = fname
        self.blob = blob
        self.tf = self._tf_open()
    
    def _tf_open(self):
        """Return a TarFile object for the provided blob."""

        return tarfile.open('r', fileobj=io.BytesIO(self.blob))

    def extract(self):
        # Avoid weird file permission issues while untarring, taken from
        # https://stackoverflow.com/questions/7237475/overwrite-existing-read-only-files-when-using-pythons-tarfile
        for f in self.tf:
            try: 
                self.tf.extract(f)
            except IOError as e:
                os.remove(f.name)
                self.tf.extract(f)
            finally:
                os.chmod(f.name, f.mode)

    def __str__(self):
        return str(self.tf.getnames())


class FSTree:
    """FS renderer and utilities."""

    def __init__(self, path='.'):
        self.path = path
    
    def traverse(self, parent_node):
        """Render the current fs within the provided DOM node."""

        global unpacked_dict

        for path, _, files in os.walk(self.path):
            # add a div to the DOM for dir
            dir_node = document.createElement('div')
            dir_node.classList.add('dir')
            dir_node.classList.add(f'depth-{len(path.split("/"))}')
            title_node = document.createElement('span')
            title_node.classList.add('title')
            title_node.innerText = path
            dir_node.appendChild(title_node)
            parent_node.appendChild(dir_node)

            for f in files:
                pathname = os.path.join(path, f)
                readable_stats, st = self._get_stats(pathname)
                
                with open(pathname, 'rb') as f:
                    data = f.read()
                unpacked_dict[pathname] = oct(st.st_mode)
                localStorage.setItem(pathname, b64e(data).decode())
                # add a div to the DOM for each file
                file_node = document.createElement('div')
                file_node.classList.add('file')
                file_node.innerText = readable_stats
                file_node.appendChild(self._render_content(pathname, data))
                dir_node.appendChild(file_node)
                
        cookie = SimpleCookie()
        cookie[COOKIE_NAME] = json.dumps(unpacked_dict)
        document.cookie = cookie[COOKIE_NAME].OutputString()

    def _render_content(self, pathname, data):
        """Return a DOM node with a rendering of the input data."""

        ext = pathname.split('.')[-1]
        if ext in IMAGE_EXTS:
            node = document.createElement('img')
            node.classList.add('file-image')
            node.src = f'data:image/{ext};base64,{b64e(data).decode()}'
        elif ext in TEXT_EXTS:
            node = document.createElement('div')
            node.classList.add('file-text')
            text_node = document.createTextNode(data.decode())
            node.appendChild(text_node)
        else:
            node = document.createElement('div')
            node.classList.add('file-unknown')
            node.classList.add('warning')
            text_node = document.createTextNode('???')
            node.appendChild(text_node)
            elog(f'Unable to read the file {pathname}')
        return node


    def _get_stats(self, pathname):
        """Get stats of the provided pathname."""

        st = os.stat(pathname)
        perms = stat.filemode(st.st_mode)
        return [f'{perms} {st.st_uid} {st.st_gid} {st.st_size} {st.st_atime} {pathname}', st]


def log(msg, cls='info'):
    """Utility to log messages, `print` is still broken in presence of event handlers."""
    
    simple_cls = ''
    if cls == 'warning': simple_cls = '!'
    elif cls == 'info': simple_cls = '*'
    else: simple_cls = cls

    pyscript.write(STDOUT, f'[{simple_cls}] {msg}', True)


def elog(msg):
    """Log warnings."""
    
    log(msg, cls='warning')


def clog(msg):
    """Print to the browser's console."""

    console.log(msg)


def tar_pack(path='.'):
    """Pack all files and make the tgz downloadable."""

    import uuid

    archive_pathname = f'{uuid.uuid4()}.tar.gz'
    with tarfile.open(archive_pathname, "w:gz") as tar:
        for pathname in unpacked_dict.keys():
            tar.add(pathname)
    with open(archive_pathname, 'rb') as f:
        data = f.read()
    os.remove(archive_pathname)

    # prepare the blob
    blob = Blob.new([to_js(data)], {type : 'application/gzip'})

    # add the link to the page
    a_node = document.createElement('a')
    a_node.appendChild(document.createTextNode('Download Archive'))
    a_node.href = URL.createObjectURL(blob)
    a_node.download = archive_pathname
    a_node.classList.add('button')
    a_node.role = 'button'
    node = document.getElementById(DOWNLOAD_COL_ID)
    node.innerHTML = ''
    node.append(a_node)     


def extract_all(files_dict):
    """Extract all provided archives."""

    for fname, blob in files_dict.items():
        # check if the file is a valid archive, only allow letters, numbers, underscore, and dash
        # followed by standard tar suffixes
        if re.match('[\w-]+\.tar((\.gz)?|(\.bz2))?', fname):
            log(f'Analyzing {fname}')
            try:
                ar = Archive(fname, blob)
                ar.extract()
            except tarfile.ReadError as e:
                elog(f'Unable to extract {fname}, maybe this archive is corrupted')
        else:
            elog(f'{fname} is not a valid archive file')


def render(node, path='.'):
    """Render the extracted files."""

    ft = FSTree(path=path)
    ft.traverse(node)


def make_fs(unpacked_dict, path='.'):
    """Recreate the fs loading resources from local storage."""

    import pathlib

    for fname, perms in unpacked_dict.items():
        b64blob = localStorage.getItem(fname)
        try:
            blob = b64d(b64blob)
        except Exception:
            elog('Invalid blob')
        if blob:
            path, _ = os.path.split(fname)
            pathlib.Path(path).mkdir(parents=True, exist_ok=True)
            with open(fname, 'wb', opener=lambda p, fs: os.open(p, fs, int(perms, 8))) as f:
                f.write(blob)
    display_unpacked()
    # disable portable URL generation, we have no archives around this time
    Element(PORTABLE_BTN_ID).add_class('hidden')


def make_portable(event):
    """Generate a portable URL that should work regardless of the browser state."""

    if not unpacked_dict:
        elog('No files present')
        return
    
    serial_files = serialize(uploaded_dict)
    try:
        portable_url = f'{str(window.location).split("#")[0]}#{serial_files}'
    except Exception as e:
        portable_url = f'{window.location}#{serial_files}'

    a_node = document.createElement('a')
    a_node.appendChild(document.createTextNode('Portable URL'))
    a_node.href = portable_url
    a_node.classList.add('button')
    node = document.getElementById(PORTABLE_COL_ID)
    node.innerHTML = ''
    node.append(a_node)


def serialize(files_dict):
    """Serialize data, x == unserialize(serialize(x))."""

    pairs = []
    for fname, blob in files_dict.items():
        pairs.append(f'{b64e(fname.encode()).decode()}@{b64e(blob).decode()}')
    
    return '.'.join(pairs)


def unserialize(serialized_data):
    """Unserialize data."""

    files_dict = dict()
    for pair in serialized_data.split('.'):
        name, value = [b64d(p) for p in pair.split('@')]
        files_dict[name.decode()] = value
    
    return files_dict


def display_unpacked():
    """Clear the drawing area, then display files and prepare the tgz."""
    
    node = document.getElementById(TREE_DIV_NODE)

    # clear the div
    node.innerHTML = ''
    # render unpacked files and prepare the final tgz
    render(node)
    tar_pack()


async def upload(event):
    """Handle the uploaded files by extracting all archives and displayng the content."""

    global uploaded_dict
    
    # get files
    file_list = event.target.files
    for file in file_list:
        buffer = await file.arrayBuffer()
        uploaded_dict[file.name] = buffer.to_bytes()
    extract_all(uploaded_dict)
    display_unpacked()
    # ensure that the portable button is enabled
    Element(PORTABLE_BTN_ID).remove_class('hidden')


def main():
    global unpacked_dict, uploaded_dict

    # register event handlers
    upload_btn = document.getElementById(UPLOAD_BTN_ID)
    upload_btn.addEventListener("change", create_proxy(upload), False)
    portable_btn = document.getElementById(PORTABLE_BTN_ID)
    portable_btn.addEventListener("click", create_proxy(make_portable), False)

    # portable URLs have priority over existing browser state
    if window.location.hash:
        uploaded_dict = unserialize(window.location.hash)
        extract_all(uploaded_dict)
        display_unpacked()
        # disable portable URL generation, we have just used it
        Element(PORTABLE_BTN_ID).add_class('hidden')
    else:
        # recover previous state if no portable URL is given
        try:
            cookie = SimpleCookie(document.cookie)[COOKIE_NAME]
            unpacked_dict = json.loads(cookie.value)
        except Exception:
            # ignore invalid cookies, assume a unpacked_dict is not provided
            pass

        if unpacked_dict:
            make_fs(unpacked_dict)

    # just wait for files to be uploaded now, greet ECSC players in the meanwhile just
    # because terminating the main function with a comment is a bit lame
    clog('Hi ECSC player, we <3 u')


main()