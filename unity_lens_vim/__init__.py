import logging
import optparse
import re
import subprocess

import gettext
from gettext import gettext as _
gettext.textdomain('unity-lens-vim')

from singlet.lens import SingleScopeLens, IconViewCategory, ListViewCategory

from unity_lens_vim import unity_lens_vimconfig

from gi import _glib
from glob import glob
from gi.repository import Gio
from os import chdir
from os.path import basename, dirname, expanduser, exists, isdir, join
from fnmatch import fnmatch
from signal import signal, SIGCHLD, SIG_IGN
from urlparse import urlparse

class VimLens(SingleScopeLens):

    class Meta:
        name = 'vim'
        description = 'Vim Lens'
        search_hint = 'Search Vim history'
        icon = 'vim.svg'
        search_on_blank = True
        category_order = ['vimfiles_category', 'filesystem_category', 'new_category']

    vim_icon = '/usr/share/app-install/icons/vim.png'
    home = expanduser('~')
    viminfo = join(home, '.viminfo')

    # ListView view shows the full path (IconViewCategory does not)
    filesystem_category = ListViewCategory('Filesystem', 'dialog-information-symbolic')
    vimfiles_category = ListViewCategory('Vim files', 'dialog-information-symbolic')
    new_category = ListViewCategory('New file', 'dialog-information-symbolic')

    # Ignore children that want to become zombies (it's for their own good)
    signal(SIGCHLD, SIG_IGN)

    def add_paths_to_results(self, results, category, paths):
        """Adds the (unexpanded) paths to the result category."""
        for path in paths:
            expanded_path = expanduser(path)
            uri = 'file://%s' % expanded_path # danger: unquoted
            results.append(expanded_path, # NB path not URI
                    self.get_icon(uri), # icon path
                    category, # view category
                    'text/plain', # MIME type
                    self.slashify(path), # text
                    '', # comment
                    uri) # for drag and drop

    def get_icon(self, uri):
        """Returns a path to an icon for the given URI."""
        g_file = Gio.file_new_for_uri(uri)
        try:
            icon = g_file.query_info(
                    Gio.FILE_ATTRIBUTE_THUMBNAIL_PATH,
                    Gio.FileQueryInfoFlags.NONE,
                    None)
        except _glib.GError: # eg file vanished
            return self.vim_icon
        icon_path = icon.get_attribute_as_string(
                Gio.FILE_ATTRIBUTE_THUMBNAIL_PATH) or self.vim_icon
        return icon_path

    def handle_uri(self, scope, uri):
        """Open the selected file with gvim."""
        #print 'Handling %s' % path
        path = urlparse(uri).path
        try:
            # In general if you can't chdir to the parent directory
            # then you won't be able to read files in that directory.
            # There might be some odd filesystems where this doesn't
            # hold, so ignore any errors from chdir(). If the directory
            # really isn't accessible then gvim will report "permission
            # denied" which is nicer than just bombing here anyway.
            chdir(dirname(path))
        except:
            pass
        subprocess.Popen(['/usr/bin/gvim', '--', uri]) # Vim opens URIs just fine cf netrw
        return self.hide_dash_response(path)

    def pattern(self, search):
        """Returns a pattern suitable for fnmatch() from search string."""
        # Anchor characters (^, $) are special here in the normal RE way.
        # A leading tilde (~) acts to indicate a user home directory (as most shells).
        # Quote a leading caret or tilde, or trailing backslash if you should want
        # to search for a filename containing one of these characters.
        # Leading special characters:
        #print search
        if re.search('^~', search): # starts with tilde
            pattern = expanduser(search) # expand leading tilde
        elif re.search('^\\\\\~', search): # starts with backslash tilde
            pattern = '*' + search[1:] # strip leading backslash before tilde
        elif re.search('^\^', search): # starts with caret
            pattern = search[1:] # strip leading caret
        elif re.search('^\\\\\^', search): # starts with backslash tilde
            pattern = '*' + search[1:] # strip leading backslash before caret
        elif re.search('^/', search):
            pattern = search
        else:
            pattern = '*' + search
        # Trailing special characters:
        if re.search('\\\\\$$', pattern): # ends with backslash dollar
            pattern = pattern[:-2] + '$*' # strip backslash before trailing dollar
        elif re.search('\$$', pattern): # ends with dollar
            pattern = pattern[:-1] # strip trailing dollar
        else:
            pattern = pattern + '*'
        return pattern

    def query_filesystem(self, search):
        """Return all matching file paths from the filesystem."""
        pattern = self.pattern(search)
        #print 'Filesystem pattern: %s' % pattern
        # Special case for search pattern that ends with / or /$: should
        # also include the directory itself in the results (assuming it
        # exists). This does not apply to the other two query methods
        # (directories that are opened in vim do not get recorded in
        # ~/.viminfo.
        dir_entries = glob(dirname(pattern)) if re.search('/\$?$', search) else []
        return sorted(dir_entries + glob(pattern))

    def query_new(self, search):
        """Return a list of files that could be created at the given search
        location or an empty list otherwise. Aim is to glob prefix directories
        for when eg user searches '/usr/loc*/bin/foo' and
        glob('/usr/loc*') == ['/usr/local']"""
        # Remove trailing slashes. /, //.../, ^/ and ^//.../ reduce to a
        # single slash whilst retaining any leading caret.
        stripped_search = re.sub('((^\^/?)|.)/*$', '\\1', search)
        dir_search = dirname(stripped_search)
        base_search = basename(stripped_search)
        dir_pattern = self.pattern(join(dir_search, '$'))
        base_pattern = self.pattern('^' + base_search)
        # Include the unglobbed patterns since fnmatch()/glob() has no
        # escape mechanism and otherwise there is no way to create a file
        # containing a wildcard character.
        return sorted(set([f for d in ([dir_search] + glob(dir_pattern))
            for f in ([join(d, base_search)] + glob(join(d, base_pattern)))
            if not exists(f)]))

    def query_viminfo(self, search, viminfo):
        """Return all matching file paths from the given viminfo file."""
        # NB file might not exist any more, this is a feature.
        pattern = self.pattern(search)
        #print 'Vim pattern: %s' % pattern
        return [f for f in self.viminfo_files(viminfo) if
                fnmatch(expanduser(f), pattern)]

    def search(self, search, results):
        """Perform the search and append to the results list."""
        #print "Searching %s for %s" % (viminfo, search)
        self.add_paths_to_results(results, self.vimfiles_category, self.query_viminfo(search, self.viminfo))
        if re.match('/|~|\^/', search):
            self.add_paths_to_results(results, self.filesystem_category, self.query_filesystem(search))
            self.add_paths_to_results(results, self.new_category, self.query_new(search))

    def slashify(self, path):
        """Append a trailing slash to the given path if it's a directory
        and doesn't have one already."""
        return path + '/' if isdir(path) and not re.search('/$', path) else path

    def viminfo_files(self, viminfo):
        """Return all file paths from the given viminfo file (excluding
        tree buffers from the NERDtree plugin)."""
        # Pass in the viminfo path to this method for easier testing.
        with open(viminfo) as v:
            return [re.sub('^> ', '', f).rstrip('\n') for f in v.readlines()
                    if re.match('> ', f) and not re.search('/NERD_tree_\d+$', f)]

