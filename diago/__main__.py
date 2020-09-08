#!/usr/bin/env python3
"""
diago - a tool for dialog-based menus.
Allows to easily create menus, execute commands, run 'expect' scripts.
© 2007–2020 Alexander "Honeyman" Myodov.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import os
import re
import sys
import warnings
from collections import namedtuple

import dialog

logger = logging.getLogger(__name__)

# How many fields must be in a tuple
FIELDS_IN_TUPLE = 4

DEFAULT_FILENAME = '~/.gorc'
DIAGO_BINARY_NAME = 'go'
DIAGO_VERSION = namedtuple('Version', ['major', 'minor', 'suffix'])(
    major=0,
    minor=9,
    suffix='alpha'
)
DIAGO_YEAR = '2007-2020'

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_SYNTAXERROR = 2

RE_nonalphadigits = re.compile(r'\W')


def FormatMenuFieldForOutput(field):
    """Convert he field of the tuple to the printable format.

    :param field field of a tuple (a single variable)
    :rtype str
    """

    if type(field) == str:
        return '"%s"' % field
    elif type(field) == list:
        return '[]'
    elif type(field) == tuple:
        return '()'
    else:
        return f'"{field}"-{type(field)}'


def FormatMenuItemForOutput(item):
    """Convert the menu item to a string ready to be printed.

    :param item the menu item (tuple)
    :rtype str
    """
    return '({})'.format(', '.join(FormatMenuFieldForOutput(i) for i in item))


def FormatMenuForOutput(menu):
    """Convert еру menu to a string ready to be printed

    :param menu menu structure (array)
    :rtype str
    """
    return f'[\n  %s\n]'.format(',\n  '.join(FormatMenuItemForOutput(i) for i in menu))


def ConvertTypeToChar(stype):
    """Convert the type field to a character designating it in the menu.

    Unhandled types are converted to '?' character

    :param stype the string containing the type of the
    :return string containing the character
    :rtype str
    """
    mapping = {
        'menu': '>',
        'execute': ' ',
        'expect': 'e',
    }
    try:
        res = mapping[stype]
    except KeyError:
        res = '?'

    return res


def MakeMenu_Iterator(menu):
    """Make an iterator over menu items."""
    max_num = len(menu)
    max_size = len(str(max_num))
    for i in range(0, len(menu)):
        item = menu[i]
        yield (item[0], "%s[%*i/%*i] %s" % (ConvertTypeToChar(item[2]), max_size, i + 1, max_size, max_num, item[1]))


def QuoteString(s):
    """For a string, decide how it should be quoted for the shell.

    :type s string
    """
    # 1. Put backslash in front of: \, $, ", `
    # 2. Put into double quotes if there are any non-alphadigits

    # 1.
    #	to_backslash = ['\\', '$', '"', '`'] # Order is important: backslash goes first!
    s = s.replace("\\", r"\\")
    s = s.replace("'", r"'\''")

    ## 2.
    if RE_nonalphadigits.search(s):
        s = "'%s'" % s

    return s


def HandleItem_Menu(d, title, menuarray, autopath=None, currentpath=None):
    """Handle the "menu"-type item.

    :param d dialog
    :param title menu title
    :param menuarray list with the items for the menu. Each item is a tuple of two elements
    :param autopath list with the path which should be browsed automatically
    :param currentpath  list containing the current path inside the menu

    :return whether succeeded or not
    :rtype boolean
    """
    if autopath is None:
        autopath = []
    if currentpath is None:
        currentpath = []

    # Validate the array
    for i in menuarray:
        if len(i) < FIELDS_IN_TUPLE:
            logger.error('The following menu item is incomplete: %s',
                         FormatMenuItemForOutput(i))
            return False

    menu_dialog = [s for s in MakeMenu_Iterator(menuarray)]
    menu_hash = {i[0]: i for i in menuarray}

    # Check for duplicating names of menu items
    if len(menu_dialog) != len(menu_hash):
        logger.error('Item names in the following menu should be unique: %s',
                     FormatMenuForOutput(menuarray))
        return False

    if autopath:
        # If path is non-empty, try it...
        cur_item = autopath.pop(0)
        (code, tag) = (d.DIALOG_OK, cur_item)
        if cur_item not in menu_hash:
            logger.error('Cannot browse into "%s"', tag)
            sys.exit(EXIT_FAILURE)
    else:
        # ... otherwise make a menu

        # Title should not be empty!
        if not title:
            title = " "

        # Append the path to the title
        title = title + "\nPath: " + ' '.join((QuoteString(i) for i in currentpath))

        (code, tag) = d.menu(
            title,
            choices=menu_dialog,
        )

    if code == d.DIALOG_OK:
        HandleMenuItem(d, menu_hash[tag], autopath, currentpath + [tag])
        return True

    elif code == d.DIALOG_CANCEL:
        print('Cancel chosen, quitting the tool.')
        return False

    elif code == d.DIALOG_ESC:
        print('Esc pressed, quitting the tool.')
        return False

    else:
        logger.error('Unknown return code from dialog: %s', code)


def HandleItem_Execute(command):
    """Handle the "execute"-type item.

    :param command command to execute
    :returns NEVER
    """
    os.system(command)


def HandleItem_Expect(script):
    """Handle the "expect"-type item.

    :param script expect-script to execute
    :returns NEVER
    """
    # Ignore this warning: we really need tmpnam() here
    warnings.filterwarnings('ignore', 'tmpnam is a potential security risk to your program', RuntimeWarning)
    fname = os.tmpnam()

    # In the beginning of the script, we must disable output to tty
    # and remove the temporary file
    script = f"""
	log_user 0
	spawn rm -f {fname}
    """ + script

    with open(fname, 'w') as expect_file:
        expect_file.write(script)
    os.system(f'expect -f {fname}')


def HandleMenuItem(d, menutuple, autopath=None, currentpath=None):
    """Process an item of the menu.

    Arguments:
        d              - dialog
        menutuple      - a tuple from the menu
        autopath=[]    - list with the path which should be browsed automatically
        currentpath=[] - list containing the current path inside the menu

    Returns:
        0              - ok
        False          - error
    """
    if autopath is None:
        autopath = []
    if currentpath is None:
        currentpath = []

    if len(menutuple) != FIELDS_IN_TUPLE:
        logger.error("The the syntax of the following item is incorrect (%s items instead of %s): %s",
                     len(menutuple), FIELDS_IN_TUPLE, FormatMenuItemForOutput(menutuple))
        return False

    (name, description, itemtype, item) = menutuple

    if itemtype == 'menu':
        # What if this does not contain a list? Then it's a error.
        if not isinstance(item, list):
            logger.error('The following item should contain a list of menu fields: %s',
                         FormatMenuItemForOutput(item))
            return False

        # It contains a list indeed. Show the submenu
        HandleItem_Menu(d, description, item, autopath, currentpath)

    elif itemtype == 'execute':
        # What if this does not contain a string to execute? Then it's a error.
        if not isinstance(item, str):
            logger.error('The following item should contain a string with the command to execute: %s',
                         FormatMenuItemForOutput(menutuple))
            return False

        HandleItem_Execute(item)

    elif itemtype == 'expect':
        # What if this does not contain a string to execute? Then it's a error.
        if not isinstance(item, str):
            logger.error('The following item should contain a string with the expect script to execute: %s',
                         FormatMenuItemForOutput(menutuple))
            return False

        HandleItem_Expect(item)
        logger.error('Unknown item type "%s" in following item: %s',
                     itemtype, FormatMenuItemForOutput(menutuple))

    else:
        return False

    return False


def PrintHelp():
    """Just print the help."""
    print(
        f'{DIAGO_BINARY_NAME} v. {DIAGO_VERSION.major}.{DIAGO_VERSION.minor}-{DIAGO_VERSION.suffix} - a tool for dialog-based menus.\n' +
        f'(C) {DIAGO_YEAR} Alexander "Honeyman" Myodov.\n' +
        '\n' +
        f'USAGE: {DIAGO_BINARY_NAME} [OPTION] [ACTION] [PATH]\n' +
        '\n' +
        'OPTIONS:\n' +
        '    -f FILE, --file FILE - use the specific file to generate a menu\n' +
        f'                           (default: {DEFAULT_FILENAME}).\n' +
        '\n' +
        'ACTIONS:\n' +
        '    -h, --help           - show this help.\n' +
        '    -t, --text           - (not working yet) show the available options\n' +
        '                           in a text form, without executing the dialog,\n' +
        '                           and without accepting the user response.\n' +
        '    -d, --dialog         - (default) use dialog to display the menus.\n' +
        '    -x, --xdialog,       - use Xdialog to display the menus.\n' +
        '    -X, --Xdialog\n' +
        '    --                   - end the option/action list; all other arguments\n' +
        '                           are interpreted as a menu path.\n' +
        'PATH:\n' +
        '    Pass the names of the menu items to quickly browse through them.\n' +
        f'    Example: use "{DIAGO_BINARY_NAME} Office Server" to automatically proceed into\n' +
        '    the "Office" menu and then execute "Server" menu item.\n' +
        '\n' +
        'Please send all the bug reports to amyodov@gmail.com.'
    )


class TextDialog:
    """Custom analog of Dialog class, capable of printing the items"""

    # Simulate constants from "dialog"
    DIALOG_OK = 0
    DIALOG_CANCEL = 1
    DIALOG_ESC = 2

    def menu(self, title, choices):
        """Generate a menu."""
        for (name, descr) in choices:
            print(descr[0] + QuoteString(name))

        sys.exit(EXIT_SUCCESS)


def main():
    MODE = ''  # may be 'dialog', 'Xdialog' or 'text'

    FILENAME = DEFAULT_FILENAME

    # This path should be followed automatically
    AUTO_PATH = []

    # Take the filename of the script
    my_filename = sys.argv.pop(0)

    mode_dict = {
        '-t': 'text',
        '--text': 'text',
        '-d': 'dialog',
        '-x': 'Xdialog',
        '-X': 'Xdialog',
        '--xdialog': 'Xdialog',
        '--Xdialog': 'Xdialog'
    }

    # Parse all the arguments
    while (sys.argv):
        arg = sys.argv.pop(0)
        if arg == '-h' or arg == '--help':
            """
            -h, --help
            """
            PrintHelp()
            sys.exit(EXIT_SUCCESS)
        elif arg in mode_dict:
            """
            Select mode
            """
            # Did we change the mode already?
            if MODE:
                logger.error('The tool is already switched to %s mode.', MODE)
                sys.exit(EXIT_SYNTAXERROR)
            MODE = mode_dict[arg]
        elif arg == '-f' or arg == '--file':
            """
            -f, --file
            """
            if not sys.argv:
                logger.error('Missing filename.')
                sys.exit(EXIT_SYNTAXERROR)

            FILENAME = sys.argv.pop(0)
        elif arg == '--':
            """
            --
            """
            AUTO_PATH = sys.argv
            break
        else:
            AUTO_PATH = [arg] + sys.argv
            break

    # Set default mode to "dialog"
    if not MODE:
        MODE = 'dialog'

    # Create main Dialog object
    try:
        if MODE == 'dialog':
            d = dialog.Dialog(dialog=MODE,
                              autowidgetsize=True)
        elif MODE == 'Xdialog':
            d = dialog.Dialog(dialog=MODE, compat='Xdialog')
        elif MODE == 'text':
            d = TextDialog()
        else:
            logger.error('Unsupported mode "%s".', MODE)
    except dialog.ExecutableNotFound:
        logger.error("Required %s executable not found.", MODE)
        sys.exit(EXIT_FAILURE)

    # Expand "~" component if needed
    FILENAME = os.path.expanduser(FILENAME)

    try:
        with open(FILENAME, 'r') as input_file:
            input_text = input_file.read()
    except IOError:
        logger.error('Cannot open the file %s, check its presence and access rights.', FILENAME)
        sys.exit(EXIT_FAILURE)
    else:
        try:
            Root = eval(input_text)
        except:
            logger.error('Cannot parse the file %s due to incorrect syntax.', FILENAME)
            sys.exit(EXIT_FAILURE)
        else:
            if type(Root) != list:
                logger.error('Root menu in the file %s must contain a list.', FILENAME)
                sys.exit(EXIT_FAILURE)

            HandleItem_Menu(d, 'Choose option:', Root, AUTO_PATH, [])


if __name__ == '__main__':
    main()
