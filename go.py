#!/usr/bin/env python

"""
go - a tool for dialog-based menus.
Allows to easily create menus, execute commands, run 'expect' scripts.
(C) Alexander "Honeyman" Myodov.
"""

import dialog
import logging
import sys, os
import warnings
import re


# How many fields must be in a tuple
FIELDS_IN_TUPLE = 4

DEFAULT_FILENAME = '~/.gorc'
MY_NAME = 'go'
MY_VERSION = {
	'major':  0,
	'minor':  9,
	'suffix':'alpha1'
	}
MY_YEAR = 2007

EXIT_SUCCESS     = 0
EXIT_FAILURE     = 1
EXIT_SYNTAXERROR = 2

RE_nonalphadigits = re.compile(r'\W')


def FormatMenuFieldForOutput(field):
	"""
	Convert field of the tuple to the printable format

	Arguments:
		field - field of a tuple (a single variable)

	Returns:
		string
	"""

	if type(field) == str:
		return '"%s"' % field
	elif type(field) == list:
		return '[]'
	elif type(field) == tuple:
		return '()'
	else:
		return '"%s"-%s' % (field, type(field))


def FormatMenuItemForOutput(item):
	"""
	Convert menu item to a string ready to be printed

	Arguments:
		item - menu item (tuple)

	Returns:
		string
	"""

	return '(%s)' % (', '.join (FormatMenuFieldForOutput(i) for i in item))


def FormatMenuForOutput(menu):
	"""
	Convert menu to a string ready to be printed

	Arguments:
		menu - menu structure (array)

	Returns:
		string
	"""

	return "[\n  %s\n]" % (',\n  '.join (FormatMenuItemForOutput(i) for i in menu))


def ConvertTypeToChar(stype):
	"""
	Convert the type field to a character designating it in the menu.
	Unhandled types are converted to '?' character

	Arguments:
		stype      - the string containing the type of the

	Returns:
		string     - containg the character
	"""
	mapping = {
		'menu':    '>',
		'execute': ' ',
		'expect':  'e',
		}

	try:
		res = mapping[stype]
	except KeyError:
		res = '?'

	return res

def MakeMenu_Iterator(menu):
	"""
	Makes an iterator over menu items
	"""

	max_num = len(menu)
	max_size = len(str(max_num))
	for i in xrange (0, len(menu)):
		item = menu[i]
		yield (item[0], "%s[%*i/%*i] %s" % ( ConvertTypeToChar(item[2]), max_size, i+1, max_size, max_num, item[1]))


def QuoteString(s):
	"""
	For a string, decide how it should be quoted for the shell.

	Arguments:
		s - string
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


def HandleItem_Menu(d, title, menuarray, autopath=[], currentpath=[]):
	"""
	Handle the "menu"-type item.

	Arguments:
		d              - dialog
		title          - menu title
		menuarray      - list with the items for the menu. Each item is a tuple of two elements
		autopath=[]    - list with the path which should be browsed automatically
		currentpath=[] - list containing the current path inside the menu

	Returns:
		bool           - succeeded or not
	"""

	# Validate the array
	for i in menuarray:
		if len(i) < FIELDS_IN_TUPLE:
			logging.error(
				"The following menu item is incomplete:\n"+
				"%s" % FormatMenuItemForOutput(i)
				)
			return False

	menu_dialog = [s for s in MakeMenu_Iterator(menuarray)]
	menu_hash = dict( [ (i[0], i) for i in menuarray] )

	# Check for duplicating names of menu items
	if len(menu_dialog) != len(menu_hash):
		logging.error(
	 		"Item names in the following menu should be unique:\n"+
			"%s" % FormatMenuForOutput(menuarray)

			)
		return False

	if autopath:
		# If path is non-empty, try it...
		cur_item = autopath.pop(0)
		(code, tag) = (d.DIALOG_OK, cur_item)
		if cur_item not in menu_hash:
			logging.error("Cannot browse into \"%s\""%tag)
			sys.exit(EXIT_FAILURE)
	else:
		# ... otherwise make a menu

		# Title should not be empty!
		if not title:
			title = " "

		# Append the path to the title
		title = title + "\nPath: " + ' '.join( (QuoteString(i) for i in currentpath) )

		(code, tag) = d.menu(
			title,
			choices = menu_dialog
			)

	if code == d.DIALOG_OK:
		HandleMenuItem(d, menu_hash[tag], autopath, currentpath + [tag])
		return True

	elif code == d.DIALOG_CANCEL:
		print "Cancel chosen, quitting the tool."
		return False

	elif code == d.DIALOG_ESC:
		print "Esc pressed, quitting the tool."
		return False

	else:
		logging.error("Unknown return code from dialog: %s" % code)


def HandleItem_Execute(command):
	"""
	Handle the "execute"-type item.

	Arguments:
		command   - command to execute

	Returns:
		NEVER
	"""

	os.system(command)


def HandleItem_Expect(script):
	"""
	Handle the "expect"-type item.

	Arguments:
		script    - expect-script to execute

	Returns:
		NEVER
	"""

	# Ignore this warning: we really need tmpnam() here
	warnings.filterwarnings('ignore', 'tmpnam is a potential security risk to your program', RuntimeWarning)
	fname = os.tmpnam()

	# In the beginning of the script, we must disable output to tty
	# and remove the temporary file
	script = """
	log_user 0
	spawn rm -f %s
    """ % (fname) + script

	expect_file = file(fname, 'w')
	expect_file.write(script)
	expect_file.close()

	os.system('expect -f %s'%fname)


def HandleMenuItem(d, menutuple, autopath=[], currentpath=[]):
	"""
	Process item of the menu.

	Arguments:
		d              - dialog
		menutuple      - a tuple from the menu
		autopath=[]    - list with the path which should be browsed automatically
		currentpath=[] - list containing the current path inside the menu

	Returns:
		0              - ok
		False          - error
	"""

	if len(menutuple) != FIELDS_IN_TUPLE:
		logging.error(
			("The the syntax of the following item is incorrect (%s items instead of %s):\n"+
			"%s") % (len(menutuple), FIELDS_IN_TUPLE, FormatMenuItemForOutput(menutuple))
			)
		return False

	(name, description, itemtype, item) = menutuple

	if itemtype == 'menu':
		# What if this does not contain a list? Then it's a error.
		if type(item) != list:
			logging.error(
				"The following item should contain a list of menu fields:\n"+
				"%s" % FormatMenuItemForOutput(item)
				)
			return False

		# It contains a list indeed. Show the submenu
		HandleItem_Menu(d, description, item, autopath, currentpath)

	elif itemtype == 'execute':
		# What if this does not contain a string to execute? Then it's a error.
		if type(item) != str:
			logging.error(
				"The following item should contain a string with the command to execute:\n"+
				"%s" % FormatMenuItemForOutput(menutuple)
				)
			return False

		HandleItem_Execute(item)

	elif itemtype == 'expect':
		# What if this does not contain a string to execute? Then it's a error.
		if type(item) != str:
			logging.error(
				"The following item should contain a string with the expect script to execute:\n"+
				"%s" % FormatMenuItemForOutput(menutuple)
				)
			return False

		HandleItem_Expect(item)

	else:
		logging.error(
			('Unknown item type "%s" in following item:\n'+
			"%s") % (itemtype, FormatMenuItemForOutput(menutuple) )
			)
		return False

	return False


def PrintHelp():
	"""
	Just print the help
	"""
	print (
		'%s v. %s.%s-%s - a tool for dialog-based menus.\n' +
		'(C) %s Alexander "Honeyman" Myodov.\n' +
		'\n' +
		'USAGE: %s [OPTION] [ACTION] [PATH]\n' +
		'\n' +
		'OPTIONS:\n' +
		'    -f FILE, --file FILE - use the specific file to generate a menu\n' +
		'                           (default: %s).\n' +
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
		'    Example: use "%s Office Server" to automatically proceed into\n' +
		'    the "Office" menu and then execute "Server" menu item.\n' +
		'\n' +
		'Please send all the bug reports to maa_public@sinn.ru.'
		) % (
			MY_NAME,                  # Version
			str(MY_VERSION['major']),
			str(MY_VERSION['minor']),
			str(MY_VERSION['suffix']),
			str(MY_YEAR),             # (C)
			MY_NAME,                  # USAGE
			DEFAULT_FILENAME,         # OPTIONS - -f
			MY_NAME,                  # PATH - Example
			)

class TextDialog(object):
	"""
	Custom analog of Dialog class, capable of printing the items
	"""

	# Simulate constants from "dialog"
	DIALOG_OK = 0
	DIALOG_CANCEL = 1
	DIALOG_ESC = 2

	def menu(self, title, choices):
		"""
		Generate a menu
		"""
		for (name, descr) in choices:
			print descr[0]+QuoteString(name)

		sys.exit(EXIT_SUCCESS)

"""
###############################################################################

                                 Main

###############################################################################
"""

MODE = '' # may be 'dialog', 'Xdialog' or 'text'

FILENAME = DEFAULT_FILENAME

# This path should be followed automatically
AUTO_PATH = []

# Take the filename of the script
my_filename = sys.argv.pop(0)

mode_dict = {
	'-t':        'text',
	'--text':    'text',
	'-d':        'dialog',
	'-x':        'Xdialog',
	'-X':        'Xdialog',
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
			logging.error('The tool is already switched to %s mode.' % MODE)
			sys.exit(EXIT_SYNTAXERROR)
		MODE = mode_dict[arg]
	elif arg == '-f' or arg == '--file':
		"""
		-f, --file
		"""
		if not sys.argv:
			logging.error('Missing filename.')
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
		d = dialog.Dialog(dialog=MODE)
	elif MODE == 'Xdialog':
		d = dialog.Dialog(dialog=MODE, compat="Xdialog")
	elif MODE == 'text':
		d = TextDialog()
	else:
		logging.error('Unsupported mode "%s".'%MODE)
except dialog.ExecutableNotFound:
	logging.error("Required %s executable not found."%MODE)
	sys.exit(EXIT_FAILURE)

# Expand "~" component if needed
FILENAME = os.path.expanduser(FILENAME)

try:
	input_file = file(FILENAME, 'r')
except IOError:
	logging.error('Cannot open the file %s, check its presence and access rights.' % FILENAME)
	sys.exit(EXIT_FAILURE)

input_text = input_file.read()
input_file.close()

try:
	Root = eval(input_text)
except:
	logging.error('Cannot parse the file %s due to incorrect syntax.' % FILENAME)
	sys.exit(EXIT_FAILURE)

if type(Root) != list:
	logging.error('Root menu in the file %s must contain a list.' % FILENAME)
	sys.exit(EXIT_FAILURE)

# Finally, go!
HandleItem_Menu(d, 'Choose option:', Root, AUTO_PATH, [])
