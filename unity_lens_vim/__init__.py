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
from os.path import dirname, expanduser, join
from fnmatch import fnmatch
from urlparse import urlparse

class VimLens(SingleScopeLens):

    class Meta:
        name = 'vim'
        description = 'Vim Lens'
        search_hint = 'Search Vim history'
        icon = 'vim.svg'
        search_on_blank = True

    vim_icon = '/usr/share/app-install/icons/vim.png'
    home = expanduser('~')
    viminfo = join(home, '.viminfo')

    # ListView view shows the full path (IconViewCategory does not)
    filesystem_category = ListViewCategory('Filesystem', 'dialog-information-symbolic')
    vimfiles_category = ListViewCategory('Vim files', 'dialog-information-symbolic')

    def add_path_to_results(self, results, category, path):
        """Adds the (unexpanded) path to the result category."""
        expanded_path = expanduser(path)
        uri = 'file://%s' % expanded_path # danger: unquoted
        results.append(expanded_path, # NB path not URI
                self.get_icon(uri), # icon path
                category, # view category
                'text/plain', # MIME type
                path, # text
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
        if re.search('^~', search):
            pattern = expanduser(search) # expand leading tilde
        elif re.search('^\\\~', search):
            pattern = '*' + search[1:] # strip leading backslash before tilde
        elif re.search('^\^', search):
            pattern = search[1:] # strip leading caret
        elif re.search('^\\\^', search):
            pattern = '*' + search[1:] # strip leading backslash before caret
        elif re.search('^/', search):
            pattern = search
        else:
            pattern = '*' + search
        # Trailing special characters:
        if re.search('\$$', pattern):
            pattern = pattern[:-1] # strip trailing dollar
        elif re.search('^\\\$', pattern):
            pattern = pattern[:-2] + '$' # strip backslash before trailing dollar
        else:
            pattern = pattern + '*'
        return pattern

    def query_filesystem(self, search):
        """Return all matching file paths from the filesystem."""
        pattern = self.pattern(search)
        #print 'Filesystem pattern: %s' % pattern
        return sorted(glob(pattern))

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
        for path in self.query_viminfo(search, self.viminfo):
            self.add_path_to_results(results, self.vimfiles_category, path)
        if re.match('/|~', search):
            for path in self.query_filesystem(search):
                self.add_path_to_results(results, self.filesystem_category, path)

    def viminfo_files(self, viminfo):
        """Return all file paths from the given viminfo file."""
        # Pass in the viminfo path to this method for easier testing.
        with open(viminfo) as v:
            return [re.sub('^> ', '', f).rstrip('\n') for f in v.readlines() if re.match('> ', f)]

