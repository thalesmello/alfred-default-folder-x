#!/usr/bin/env python3
# encoding: utf-8
#
# Copyright (c) 2016 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2016-03-22
# Updated 2025 for Python 3 / modern macOS (no Python 2, no Alfred-Workflow)
#

"""dfx.py [-t <type>...] [<query>]

Usage:
    dfx.py [-t <type>...] [<query>]
    dfx.py -u
    dfx.py -h | --help
    dfx.py --version

Options:
    -t <TYPE>, --type=<TYPE>  Show only items of type. May be "fav", "rfile",
                              "rfolder" or "all" [default: all].
    -u, --update              Update cached data.
    -h, --help                Show this message and exit.
    --version                 Show version number and exit.

Show and search Default Folder X favourites and recent items.

This script is self-contained: it has no third-party dependencies and
runs on the system Python 3 shipped with macOS.
"""

import json
import logging
import os
import subprocess
import sys
import time

# --------------------------------------------------------------------
# Configuration

# Where data will be cached
DFX_CACHE_KEY = 'dfx-entries'
MAX_CACHE_AGE = 10  # seconds

HELP_URL = 'https://github.com/deanishe/alfred-default-folder-x/issues'

ICON_WARNING = 'alert_caution.png'
ICON_WARNING_PATH = ('/System/Library/CoreServices/CoreTypes.bundle/'
                     'Contents/Resources/AlertCautionBadgeIcon.icns')

WORKFLOW_DIR = os.path.dirname(os.path.abspath(__file__))

log = logging.getLogger('dfx')

ERROR_CACHE_KEY = 'dfx-error'


class DFXError(Exception):
    """Raised if Default Folder X can't be reached."""


# --------------------------------------------------------------------
# Helpers


def workflow_version():
    """Return workflow version from `version` file (if any)."""
    path = os.path.join(WORKFLOW_DIR, 'version')
    try:
        with open(path) as fp:
            return fp.read().strip()
    except IOError:
        return 'unknown'


def cache_dir():
    """Return (and create) the workflow's cache directory."""
    path = os.getenv('alfred_workflow_cache')
    if not path:
        bundle_id = os.getenv('alfred_workflow_bundleid') or \
            'net.deanishe.alfred-dfx'
        path = os.path.expanduser(
            '~/Library/Caches/com.runningwithcrayons.Alfred/'
            'Workflow Data/' + bundle_id)

    os.makedirs(path, exist_ok=True)
    return path


def cache_path(name):
    """Return path to cache file `name`."""
    return os.path.join(cache_dir(), name + '.json')


def setup_logging():
    """Log to the workflow's log file and STDERR."""
    logdir = os.getenv('alfred_workflow_data') or cache_dir()
    os.makedirs(logdir, exist_ok=True)
    logfile = os.path.join(logdir, 'dfx.log')

    fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s',
                            datefmt='%H:%M:%S')

    handlers = []
    try:
        fh = logging.FileHandler(logfile, encoding='utf-8')
        handlers.append(fh)
    except IOError:
        pass

    handlers.append(logging.StreamHandler())

    for h in handlers:
        h.setFormatter(fmt)
        log.addHandler(h)

    log.setLevel(logging.DEBUG if os.getenv('alfred_debug') == '1'
                 else logging.INFO)


# --------------------------------------------------------------------
# Caching


def cache_data(key, data):
    """Save `data` (JSON-serialisable) to cache under `key`."""
    path = cache_path(key)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fp:
        json.dump(data, fp)
    os.replace(tmp, path)
    log.debug('cached %d items to %s', len(data), path)


def cached_data(key):
    """Return cached data for `key` or `None`."""
    path = cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as fp:
            return json.load(fp)
    except (ValueError, IOError) as err:
        log.warning('could not load cache %s: %s', path, err)
        return None


def cached_data_fresh(key, max_age):
    """Return `True` if cached data for `key` is younger than `max_age`."""
    path = cache_path(key)
    if not os.path.exists(path):
        return False
    return (time.time() - os.stat(path).st_mtime) < max_age


# --------------------------------------------------------------------
# Background job control


def pid_path(name):
    return os.path.join(cache_dir(), name + '.pid')


def is_running(name):
    """Return `True` if background job `name` is running."""
    path = pid_path(name)
    if not os.path.exists(path):
        return False

    try:
        with open(path) as fp:
            pid = int(fp.read().strip())
    except (ValueError, IOError):
        return False

    try:
        os.kill(pid, 0)
    except OSError:
        try:
            os.unlink(path)
        except OSError:
            pass
        return False

    return True


def run_in_background(name, args):
    """Run `args` in a detached background process."""
    if is_running(name):
        log.debug('job %r already running', name)
        return

    log.debug('starting background job %r: %r', name, args)
    devnull = subprocess.DEVNULL
    proc = subprocess.Popen(args, cwd=WORKFLOW_DIR, stdin=devnull,
                            stdout=devnull, stderr=devnull,
                            start_new_session=True)

    with open(pid_path(name), 'w') as fp:
        fp.write(str(proc.pid))


# --------------------------------------------------------------------
# Default Folder X data


def get_dfx_data():
    """Return DFX favourites and recent items.

    Returns:
        list: Sequence of dicts with `type`, `path`, `name` and
            `pretty_path` keys.
    """
    st = time.time()
    script = os.path.join(WORKFLOW_DIR, 'DFX Files.scpt')
    proc = subprocess.run(['/usr/bin/osascript', script],
                          capture_output=True)

    if proc.returncode != 0:
        err = proc.stderr.decode('utf-8', 'replace').strip()
        log.error('osascript failed: %s', err)
        if 'isn’t running' in err or "isn't running" in err or '-600' in err:
            raise DFXError('Default Folder X is not running')
        if '-1728' in err or '-1743' in err:
            raise DFXError('Alfred is not allowed to control '
                           'Default Folder X')
        raise DFXError(err.split('\n')[-1] or 'Could not talk to '
                       'Default Folder X')

    output = proc.stdout.decode('utf-8')
    log.debug('DFX files updated in %0.3fs', time.time() - st)

    entries = []
    home = os.path.expanduser('~')

    for line in [s.strip() for s in output.split('\n') if s.strip()]:
        row = line.split('\t')
        if len(row) != 2:
            log.warning('Invalid output from DFX : %r', line)
            continue

        typ, path = row
        # Remove trailing slash from path or things go wrong...
        path = path.rstrip('/')
        entries.append({
            'type': typ,
            'path': path,
            'name': os.path.basename(path),
            'pretty_path': path.replace(home, '~'),
        })

    log.debug('%d entries from DFX', len(entries))
    return entries


def do_update():
    """Update cached DFX files and folders."""
    log.info('Updating DFX data...')
    try:
        entries = get_dfx_data()
    except DFXError as err:
        cache_data(ERROR_CACHE_KEY, {'error': str(err)})
        raise
    else:
        cache_data(DFX_CACHE_KEY, entries)
        cache_data(ERROR_CACHE_KEY, {})
    finally:
        try:
            os.unlink(pid_path('update'))
        except OSError:
            pass


# --------------------------------------------------------------------
# Filtering


def path_exists(path):
    """Return `True` if `path` exists.

    Unlike `os.path.exists()`, permission errors (e.g. macOS privacy
    protections) don't cause a path to be reported as missing.
    """
    try:
        os.lstat(path)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def score(query, value):
    """Fuzzy-match `query` against `value`. Return score (0 = no match)."""
    q = query.lower()
    v = value.lower()

    if not q:
        return 100.0

    # Exact match
    if q == v:
        return 100.0
    # Prefix match
    if v.startswith(q):
        return 90.0 - (len(v) - len(q)) / 100.0
    # Substring match
    idx = v.find(q)
    if idx > -1:
        return 80.0 - idx / 10.0 - (len(v) - len(q)) / 100.0

    # Initials of "words"
    initials = ''.join([s[0] for s in
                        v.replace('-', ' ').replace('_', ' ')
                        .replace('.', ' ').split() if s])
    if initials.startswith(q):
        return 70.0

    # Fuzzy: all query chars appear in order
    pos = 0
    gaps = 0
    for ch in q:
        idx = v.find(ch, pos)
        if idx < 0:
            return 0.0
        gaps += idx - pos
        pos = idx + 1

    return max(1.0, 60.0 - gaps / 2.0)


def filter_entries(query, entries, min_score=30.0):
    """Return `entries` matching `query`, best matches first."""
    results = []
    for e in entries:
        s = score(query, e['name'])
        if s >= min_score:
            results.append((s, e))

    results.sort(key=lambda t: (-t[0], t[1]['name'].lower()))
    return [e for _, e in results]


# --------------------------------------------------------------------
# Alfred output


class Feedback:
    """Collect and emit Alfred Script Filter JSON."""

    def __init__(self):
        self.items = []
        self.rerun = None
        self.variables = {}

    def add_item(self, title, subtitle='', arg=None, uid=None, valid=False,
                 icon=None, icontype=None, copytext=None, largetext=None,
                 type=None, quicklookurl=None):
        item = {'title': title, 'subtitle': subtitle, 'valid': valid}

        if arg is not None:
            item['arg'] = arg
        if uid is not None:
            item['uid'] = uid
        if type is not None:
            item['type'] = type
        if quicklookurl is not None:
            item['quicklookurl'] = quicklookurl

        if icon is not None:
            d = {'path': icon}
            if icontype:
                d['type'] = icontype
            item['icon'] = d

        text = {}
        if copytext is not None:
            text['copy'] = copytext
        if largetext is not None:
            text['largetype'] = largetext
        if text:
            item['text'] = text

        self.items.append(item)
        return item

    def send(self):
        d = {'items': self.items}
        if self.rerun:
            d['rerun'] = self.rerun
        if self.variables:
            d['variables'] = self.variables

        json.dump(d, sys.stdout, ensure_ascii=False)
        sys.stdout.write('\n')
        sys.stdout.flush()


def prefix_name(entry):
    """Prepend a Unicode icon to entry name based on its type."""
    if entry['type'] == 'fav':
        prefix = '\U00002764'  # HEAVY BLACK HEART
    else:
        prefix = '\U0001F55E'  # CLOCK FACE THREE-THIRTY

    return '{} {}'.format(prefix, entry['name'])


# --------------------------------------------------------------------
# Argument parsing


def parse_args(argv):
    """Minimal replacement for the old `docopt` call."""
    types = []
    query_parts = []
    update = False

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ('-h', '--help'):
            print(__doc__.strip())
            sys.exit(0)
        elif arg == '--version':
            print(workflow_version())
            sys.exit(0)
        elif arg in ('-u', '--update'):
            update = True
        elif arg in ('-t', '--type'):
            i += 1
            if i >= len(argv):
                print('error: --type requires an argument', file=sys.stderr)
                sys.exit(1)
            types.append(argv[i])
        elif arg.startswith('--type='):
            types.append(arg.split('=', 1)[1])
        elif arg.startswith('-t') and len(arg) > 2:
            types.append(arg[2:])
        else:
            query_parts.append(arg)
        i += 1

    return {
        '--update': update,
        '--type': types or ['all'],
        '<query>': ' '.join(query_parts).strip(),
    }


# --------------------------------------------------------------------
# Main


def main():
    args = parse_args(sys.argv[1:])
    log.debug('args=%r', args)

    if args['--update']:
        return do_update()

    query = args['<query>']
    types = args['--type']

    fb = Feedback()

    # Load cached entries first and start update if they've
    # expired (or don't exist)
    entries = cached_data(DFX_CACHE_KEY)
    if entries is None or not cached_data_fresh(DFX_CACHE_KEY, MAX_CACHE_AGE):
        run_in_background('update',
                          [sys.executable, os.path.join(WORKFLOW_DIR,
                                                        'dfx.py'),
                           '--update'])

    # Tell Alfred to re-run the Script Filter if cache is being updated
    if is_running('update'):
        fb.rerun = 1

    # Something went wrong talking to DFX. Show the error.
    err = (cached_data(ERROR_CACHE_KEY) or {}).get('error')
    if err and entries is None:
        fb.add_item(err, 'Make sure Default Folder X is installed & running',
                    icon=ICON_WARNING_PATH)
        fb.send()
        return 0

    # No data in cache yet. Show warning and exit.
    if entries is None:
        fb.add_item('Waiting for Default Folder X data…',
                    'Please try again in a second or two',
                    icon=ICON_WARNING_PATH)
        fb.send()
        return 0

    # Filter entries by type
    if types != ['all']:
        log.debug('Filtering for types : %r', types)
        entries = [e for e in entries if e['type'] in types]

    # Remove duplicates and non-existent files
    seen = set()
    unique = []
    for e in entries:
        if e['path'] in seen:
            continue
        seen.add(e['path'])
        if path_exists(e['path']):
            unique.append(e)
    entries = unique

    # Filter data against query if there is one
    if query:
        total = len(entries)
        entries = filter_entries(query, entries)
        log.info('%d/%d entries match `%s`', len(entries), total, query)

    if not entries:
        fb.add_item('Nothing found', 'Try a different query?',
                    icon=ICON_WARNING_PATH)

    for e in entries:
        title = prefix_name(e) if types == ['all'] else e['name']

        fb.add_item(
            title,
            e['pretty_path'],
            arg=e['path'],
            uid=e['path'],
            copytext=e['path'],
            largetext=e['path'],
            type='file',
            valid=True,
            quicklookurl=e['path'],
            icon=e['path'],
            icontype='fileicon',
        )

    fb.send()
    return 0


if __name__ == '__main__':
    setup_logging()
    try:
        sys.exit(main() or 0)
    except Exception as err:  # noqa
        log.exception('workflow error: %s', err)
        # Only Script Filters can show feedback
        if '--update' not in sys.argv and '-u' not in sys.argv:
            fb = Feedback()
            fb.add_item('Error: {}'.format(err), 'Check the log for details',
                        icon=ICON_WARNING_PATH, valid=True, arg=HELP_URL)
            fb.send()
        sys.exit(1)
