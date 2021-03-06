# Diago: convenient menu based on `dialog`

## OVERVIEW

Diago is a tool which allows to easily create hierarchy of menus, and browse
such menus. The name of the tool means “DIAlog GO” – the tool “go”, which is
actually a frontend over another tool, “dialog”.

For example, imagine, you have a lot of accounts on a bunch of Unix servers,
and need to be able to connect to each of them, but do not want to remember
all the hostnames, logins and passwords. Now you can create a menu listing all
of the servers, put the required commands/scripts to connect there, and after
that just call a short command (“`diago`” or “`diago.py`”, or even “`g`”) – the menu with the list will
be displayed, and you just choose the needed destination, and voila, you are
connected! Moreover, you can group such servers and create submenus, you can
make each server into a menu if there are several ways to access it…
But usages for such menus are numerous – they may be used anywhere if you want
to put the large amount of information into a file once, and then choose one
from a menu. Put all your sysadmin commands into a large menu, so that you only
choose between them, rather than remember the long command lines and argument
lists? Automate your typical actions? Do whatever you want with this tool – it
is just a hammer, and it is you who decide what nails to hit.

## USAGE

Diago is a Python program (called “`diago`”, but, for your convenience, you are
highly suggested to make an alias like `g` referring to it, if it is not
done already by the maintainer of this package; the following description
assumes that it is done already, and the tool can be executed by “`diago`” command).
It may be called with or without command line options; calling the tool by just
“`diago`” displays a menu in your console, and the “default” menu is generated, upon
the configuration file “`~/diago/config`”.
Additional options let you decide whether a console menu or graphical menu is
generated, select the file which stores the structure of your menu, and
even automatically browse into deeper level of generated menu.

## HISTORY

This tool appeared due after the experience of using a great SecureCRT terminal in Windows, and the lack of the tools
that would allow to create a simple “menu to remotely log in” in Linux. Initially (in 2007) it has been called just
“`go`” (as in, “you can go anywhere with this tool”), but then renamed to “`diago`” in 2009,
after the appearance of Go programming language which used the `go` binary extensively for its own purposes.

In practice, making an alias to just `g` is even better than `go`. 

## OPTIONS

### -f FILE, --file FILE

You can use this option if you want to generate a menu from the information
stored in the specified file. Calling “`go`” without “`-f`” or “`--file`” option is
equal to calling “`go -f ~/.diago/config`”. The structure of such files is described
below, in the section “`MENU STRUCTURE`”. Do not forget that you may create
aliases in your shell, for example (in bash):

    alias goapache="diago -f ~/.diago-apacheconfig"

## MENU STRUCTURE

You likely will create at least one file describing the menu structure,
“`~/.diago/config`”. This will be the default file used by diago. But you can create
multiple files, and call “`go`” with option “`-f FILENAME`”, executing appropriate
menus.
The file with the menu structure contains the following distinct syntax
components: <menu> (including root menu), <menu option>, <menu option parts>
and <whitespaces>. In fact, the only what should contain the file is the root
menu, which is <menu> from the syntax viewpoint.

### <Menu>

<Menu> is the (surrounded with square brackets) set of <menu options>,
delimited with commas: `[ OPTION1, OPTION2, OPTION3, ... OPTION_N ]`.
Real-life example:

    [
      ('action1', 'action1 description', 'execute', 'echo o1'),
      ('action2', 'action2 description', 'execute', 'echo o2')
    ]

Usually (and this is suggested for readability) each <menu option> is written
on a separate line in the file (because each <menu option> stands for a row
in the displayed menu).

### <Menu option>

<Menu option> contains 4 (surrounded with round brackets) <menu option parts>,
delimited with commas: ( OPTPART1, OPTPART2, OPTPART3, OPTPART4 ).
Real-life example:

    ('action1', 'action1 description', 'execute', 'echo o1')

Option part 1 is the Option Name (which must be unique within each level
of menu/submenu) – this is displayed on the left part of the displayed menu
and is the required field;
Option part 2 is the Option Description – it is displayed on the right part
of the displayed menu and may be omitted;
Option part 3 is the Option Type; currently it accepts the following values:
`'execute'`, `'expect'`, `'menu'`;
Option part 4 is the Option Value; depending upon the Option Type, it contains
either a text string or a submenu.

If Option Type is `'execute'` for some option in a menu, the Option Value
must contain the string with a shell command (or several commands), which
will be executed when this option is chosen in the menu.

If Option Type is `'expect'` for some option in a menu, the Option Value
must contain the string containing the expect script which will be executed
when this option is chosen in the menu. For details on the expect syntax,
read the documents on expect interpreter and consult the official
expect website at http://expect.nist.gov.

If Option Type is `'menu'` for some option in a menu, the Option Value must
contain the submenu, which is just a usual <menu> from the syntax viewpoint.
Real-life example of a <menu option> with a submenu:

    ('menu1', 'menu1 description', 'menu', [
        ('submenu action1', 'action1 description', 'execute', 'echo 1')
        ('submenu action2', 'action1 description', 'execute', 'echo 1')
    ])

### <Menu option part>

<Menu option part> is usually the string (the only exception,
described already, is the Option Value, in case if Option Type is `'menu'`)
containing some text. The string syntax rules are equal to those in Python,
but if you don't know Python – the string may be surrounded with single or
double quotes, may contain escape sequences similarly to other languages
(which are interpreted in single-quoted-strings and double-quoted-strings
equally, unlike in C/C++), like \n, \r, \'', \" or \\. It also may contain
the following escape sequences:
  
  * \xhh – character with hex value hh,
  * \ooo – character with octal value ooo,
  * \N{name} – character named name in the Unicode database
            (Unicode string only, see below)
  * \uxxxx   – character with 16-bit hex value xxxx (Unicode strings only,
             see below),
  * \Uxxxxxxxx – character with 32-bit hex value xxxxxxxx (Unicode strings
               only, see below),

The opening string quote may be prefixed with `u` or `U` symbol, what makes
it a “Unicode string”, for example: `u'Hello world \N{dram}'`. Such string may
accept Unicode characters, and also \N{name}, \uxxxx and \Uxxxxxxxx escape
sequences.

The opening string quote may also be prefixed with `r` or `R` symbol, what
makes it a “raw” string, for example: `r'Hello world'`. Within such “raw”
strings, the character following the backslash symbol (unless the backslash
symbol is the last symbol in the string) is not interpreted, that is `r'\n'
string mean a string with two symbols, “backslash” and “`n`”.

If raw modifier is used together with Unicode modifier, Unicode modifier
should go first, for example: `ur'Hello world'`.

The string may also be surrounded with triple single-quotes
(or double-quotes); within such triple quotes, the escape symbols are not
interpreted, backslash symbol is left as is, and single and double quotes can
be used freely (until there are no more than three them in a row, what
stands for the end of triple-quotes string). This is especially useful for
embedding the expect scripts into the menu (value “`expect`” for the
Option Type).

Example:

    send_user "Connecting to server...\n"
    set timeout 60
    spawn ssh server.tld
    interact
  
### <Whitespaces>

Any whitespace symbols (space, newline, tabulation, etc) may be freely used
between <menu option parts> and <menu options>.
