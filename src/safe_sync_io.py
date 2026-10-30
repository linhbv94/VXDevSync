"""Sync I/O boundaries. Vendored identically in the standalone skills CLI.

POSIX parents are descriptor-anchored and opened without following links.
Windows holds ancestor handles without delete sharing and rejects reparse points.
Files are published by replacing an entry, never truncating an existing inode.
"""
from contextlib import contextmanager, ExitStack
import hashlib
import errno
import os
from pathlib import Path
import shutil
import stat
import uuid

_SYSTEM_ALIASES = ({Path(p): Path(os.path.realpath(p)) for p in ('/var', '/tmp', '/etc')}
                   if os.name != 'nt' else {})


def _reject_link(info):
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('Không đồng bộ qua symlink/reparse point; hãy dùng thư mục và tệp thường.')


def _root(path):
    path = Path(os.path.abspath(path))
    try:
        _reject_link(path.lstat())
    except FileNotFoundError:
        pass
    # Only normalize fixed OS aliases, never a configurable/user-writable parent:
    # resolving that parent could follow an agent directory swapped to a symlink.
    for alias, physical in _SYSTEM_ALIASES.items():
        try:
            path = physical / path.relative_to(alias)
            break
        except ValueError:
            continue
    return path


@contextmanager
def _win_handle(path, directory):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    class Attributes(ctypes.Structure):
        _fields_ = [('attributes', wintypes.DWORD), ('tag', wintypes.DWORD)]
    inspect = kernel.GetFileInformationByHandleEx
    inspect.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    inspect.restype = wintypes.BOOL
    # OPEN_REPARSE_POINT prevents following the final component. Ancestors are
    # already held by the directory chain; omitting FILE_SHARE_DELETE pins them.
    handle = create(str(path), 0x80 if directory else 0x80000000,
                    3 if directory else 1, None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attrs = Attributes()
        if not inspect(handle, 9, ctypes.byref(attrs), ctypes.sizeof(attrs)):
            raise ctypes.WinError(ctypes.get_last_error())
        if attrs.attributes & 0x400 or bool(attrs.attributes & 0x10) != directory:
            raise ValueError('Không đồng bộ reparse point hoặc kiểu tệp không hợp lệ.')
        yield handle
    finally:
        close(handle)


@contextmanager
def _directory(path, create=False):
    path = Path(path)
    with ExitStack() as stack:
        if os.name == 'nt':
            current = Path(path.anchor)
            stack.enter_context(_win_handle(current, True))
            for part in path.parts[1:]:
                current /= part
                if create:
                    try:
                        current.mkdir()
                    except FileExistsError:
                        pass
                stack.enter_context(_win_handle(current, True))
            yield current
        else:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            fd = os.open(path.anchor, flags)
            stack.callback(os.close, fd)
            for part in path.parts[1:]:
                if create:
                    try:
                        os.mkdir(part, dir_fd=fd)
                    except FileExistsError:
                        pass
                fd = os.open(part, flags, dir_fd=fd)
                stack.callback(os.close, fd)
            yield fd


def _relative(relative):
    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or any(p in ('.', '..') for p in relative.parts):
        raise ValueError('Đường dẫn sync nằm ngoài phạm vi.')
    return relative


@contextmanager
def _parent(root, relative, create=False):
    relative = _relative(relative)
    root = _root(root)
    # The root itself must be checked even if the file is deeply nested.
    with _directory(root, create):
        with _directory(root / relative.parent, create) as parent:
            yield parent, relative.name


@contextmanager
def _read(parent, name):
    if os.name == 'nt':
        with _win_handle(parent / name, False):
            with open(parent / name, 'rb') as stream:
                yield stream
    else:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except OSError as error:
            if error.errno in (errno.ELOOP, errno.ENOTDIR):
                raise ValueError('Không đọc rules/skill qua symlink hoặc đường dẫn không an toàn.') from error
            raise
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('Chỉ đồng bộ tệp thường.')
            yield stream


def ensure_directory(root):
    with _directory(_root(root), True):
        pass


def validate_tree(root, ignored):
    root = _root(root)
    if not root.exists():
        return
    with _directory(root):
        for current, directories, files in os.walk(root, followlinks=False):
            directories[:] = [name for name in directories
                              if name not in ('.system', '.git')
                              and not ignored((Path(current) / name).relative_to(root))]
            for name in directories + files:
                path = Path(current) / name
                if ignored(path.relative_to(root)):
                    continue
                info = path.lstat()
                _reject_link(info)
                if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                    raise ValueError('Cây sync chứa kiểu tệp không hỗ trợ.')


def file_hash(root, relative):
    try:
        with _parent(root, relative) as (parent, name), _read(parent, name) as stream:
            digest = hashlib.md5()
            for block in iter(lambda: stream.read(65536), b''):
                digest.update(block)
            return digest.hexdigest()
    except FileNotFoundError:
        return ''


def _stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read_text(root, relative):
    with _parent(root, relative) as (parent, name), _read(parent, name) as stream:
        return stream.read().decode('utf-8')


def write_text(root, relative, text, mtime=None):
    with _parent(root, relative, True) as (parent, name):
        mode = 0o644
        try:
            info = (parent / name).lstat() if os.name == 'nt' else os.stat(name, dir_fd=parent, follow_symlinks=False)
            _reject_link(info)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('Đích rules phải là tệp thường.')
            mode = stat.S_IMODE(info.st_mode)
        except FileNotFoundError:
            pass
        temporary = '.sync_stage_' + uuid.uuid4().hex
        stage = parent / temporary if os.name == 'nt' else temporary
        kwargs = {} if os.name == 'nt' else {'dir_fd': parent}
        try:
            fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, **kwargs)
            with os.fdopen(fd, 'wb') as output:
                output.write(text.encode('utf-8'))
                output.flush()
                if os.name != 'nt':
                    os.fchmod(fd, mode)
                    if mtime is not None:
                        os.utime(fd, (mtime, mtime))
                os.fsync(fd)
            if os.name == 'nt':
                os.chmod(stage, mode)
                if mtime is not None:
                    os.utime(stage, (mtime, mtime))
                os.replace(stage, parent / name)
            else:
                os.replace(stage, name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
        finally:
            try:
                os.unlink(stage, **kwargs)
            except FileNotFoundError:
                pass


def copy_file(source_root, destination_root, relative):
    with _parent(source_root, relative) as (sp, sn), _read(sp, sn) as source:
        before = os.fstat(source.fileno())
        with _parent(destination_root, relative, True) as (dp, dn):
            # Refuse existing symlinks. A link swapped in later is still safe:
            # replace changes that entry instead of following it to a victim.
            try:
                target = (dp / dn).lstat() if os.name == 'nt' else os.stat(dn, dir_fd=dp, follow_symlinks=False)
                _reject_link(target)
                if not stat.S_ISREG(target.st_mode):
                    raise ValueError('Đích sync phải là tệp thường.')
            except FileNotFoundError:
                pass
            temporary = '.sync_stage_' + uuid.uuid4().hex
            stage = dp / temporary if os.name == 'nt' else temporary
            kwargs = {} if os.name == 'nt' else {'dir_fd': dp}
            try:
                fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, **kwargs)
                with os.fdopen(fd, 'wb') as output:
                    shutil.copyfileobj(source, output)
                    if _stamp(os.fstat(source.fileno())) != _stamp(before):
                        raise ValueError('Tệp nguồn thay đổi trong lúc sync; chưa thay tệp đích.')
                    output.flush()
                    if os.name != 'nt':
                        os.fchmod(output.fileno(), stat.S_IMODE(before.st_mode))
                    # copy2 also preserves file times; keep newest-file selection stable.
                    if os.name == 'nt':
                        os.utime(stage, ns=(before.st_atime_ns, before.st_mtime_ns))
                    else:
                        os.utime(output.fileno(), ns=(before.st_atime_ns, before.st_mtime_ns))
                        # Best-effort extended attributes, like shutil.copy2, but
                        # through the already-open files rather than path lookup.
                        if hasattr(os, 'listxattr'):
                            try:
                                for attribute in os.listxattr(source.fileno()):
                                    try:
                                        os.setxattr(output.fileno(), attribute, os.getxattr(source.fileno(), attribute))
                                    except OSError:
                                        pass
                            except (OSError, TypeError):
                                pass
                    os.fsync(output.fileno())
                if os.name == 'nt':
                    os.chmod(stage, stat.S_IMODE(before.st_mode))
                    os.replace(stage, dp / dn)
                else:
                    os.replace(stage, dn, src_dir_fd=dp, dst_dir_fd=dp)
                    os.fsync(dp)
            finally:
                try:
                    os.unlink(stage, **kwargs)
                except FileNotFoundError:
                    pass
