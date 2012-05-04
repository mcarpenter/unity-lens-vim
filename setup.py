#!/usr/bin/env python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

###################### DO NOT TOUCH THIS (HEAD TO THE SECOND PART) ######################

import os
import sys

try:
    import DistUtilsExtra.auto
    from DistUtilsExtra.command import build_extra
except ImportError:
    print >> sys.stderr, 'To build vim you need https://launchpad.net/python-distutils-extra'
    sys.exit(1)
assert DistUtilsExtra.auto.__version__ >= '2.18', 'needs DistUtilsExtra.auto >= 2.18'

def update_config(values = {}):

    oldvalues = {}
    try:
        fin = file('vim/vimconfig.py', 'r')
        fout = file(fin.name + '.new', 'w')

        for line in fin:
            fields = line.split(' = ') # Separate variable from value
            if fields[0] in values:
                oldvalues[fields[0]] = fields[1].strip()
                line = "%s = %s\n" % (fields[0], values[fields[0]])
            fout.write(line)

        fout.flush()
        fout.close()
        fin.close()
        os.rename(fout.name, fin.name)
    except (OSError, IOError), e:
        print ("ERROR: Can't find vim/vimconfig.py")
        sys.exit(1)
    return oldvalues


class InstallAndUpdateDataDirectory(DistUtilsExtra.auto.install_auto):
    def run(self):
        values = {'__vim_data_directory__': "'%s'" % (self.prefix + '/share/vim/'),
                  '__version__': "'%s'" % (self.distribution.get_version())}
        previous_values = update_config(values)
        DistUtilsExtra.auto.install_auto.run(self)
        update_config(previous_values)


        
##################################################################################
###################### YOU SHOULD MODIFY ONLY WHAT IS BELOW ######################
##################################################################################

DistUtilsExtra.auto.setup(
    name='vim',
    version='0.1',
    #license='GPL-3',
    #author='Your Name',
    #author_email='email@ubuntu.com',
    #description='UI for managing …',
    #long_description='Here a longer description',
    #url='https://launchpad.net/vim',
    data_files=[
        ('share/unity/lenses/vim', ['vim.lens']),
        ('share/dbus-1/services', ['unity-lens-vim.service']),
        ('share/unity/lenses/vim', ['unity-lens-vim.svg']),
        ('bin', ['bin/vim']),
    ],
    cmdclass={"build":  build_extra.build_extra, 'install': InstallAndUpdateDataDirectory}
    )

