Dewaste
=======
As shocking as it may sound, walking barefoot on grass was common in the past. Looking around now, all we can see are mountains made of junk. Former generations romanticized rainy days and the smell of wet ground in the air after a storm. Those generations also made it impossible for us to live the same experiences. Rain is acid, and the land is buried under tens of meters of rubbish.

We could not stand this new norm anymore. We hated being in constant danger because of hazardous materials lying around. And we hated being unable to produce medical equipment to cure our beloved ones due to the lack of natural resources on the Planet. But hatred alone brings further destruction, turning people blind and preventing them from realizing the obvious. Indeed, the solution coincided with the problem. All the electronic junk assembled over the centuries is an open-pit mine that we can recycle for good.

Welcome to DEWASTE.


Description
-----------
This services resembles the end-user facing interface of a recycling plant.
It is meant to be used by end-users to learn about what the recycling plant is all about and to register stuff for 
recycling.

User Stories:
* A user comes to the webpage and wants to learn about what the recycling plant does and how it works.
(FAQ section and informational pages)
* A user can register a physical item, which the user will bring to the physical location later.
This is useful to reduce waiting times and filling out forms at the location.
* A user can upload digital items, which are processed by the recycling plant.
* A user can see the results of the processing done to owned digital items.
* A user can register an account, to view the status of registered items and being placed on a leaderboard.


Flag stores
-----------
In this service we have two flag stores. 
One on the server side inside the database and one in the browser of an "innocent" user. 

### Postgres DB
There are multiple ways to get full read access inside the database.
Inside the database could be on different places.

1. Serial number of physical items
2. Inside the data blob of digital items

### Browser
Flags are contained in tar files uploaded by a browser. Flags will be stores either as txt files or 
as images contained in the archive. Uncompressed data is stored in the local storage of the browser.


Vulnerabilities & Patches (Flag store 1)
----------------------------------------

### Vuln 1 - Broken Access Control

When a user registers an item, but does not want to create an account, an authentication token is generated, for the particular item. The user is presented a link which contains this token.
The vulnerability is, that items registered by users do not get such an authentication token generated. In the database we have an empty string. The logic for viewing items does not check whether an authentication token is present, so users can access items of users when supplying an empty authentication token.

The patches have to be applied for physical and digital items separately.

#### Patch 1 - Every item gets a token

In `DigitalItemRegistrationService::register` and `PhysicalItemRegistrationService::register` at:
```php
if ($user === null) {
    $item->authToken = bin2hex(openssl_random_pseudo_bytes(20));
}
```
just remove the `if` around the statement.
As old items still do not have an authentication token, they have to be added in the database directly.

#### Patch 2 - Do not allow empty authentication tokens when viewing items

In `RecycleController::myPhysicalItem` and `RecycleController::myDigitalItem` change
```php
...
} elseif ($authToken !== null && $physicalItem->authToken === $authToken) {
    // all good
} else {
...
```
to
```php
...
} elseif ($authToken !== null && $physicalItem->authToken !== "" && $physicalItem->authToken === $authToken) {
    // all good
} else {
...
```

### Vuln 2 - SQLi by exploiting weak PNGR

The `QueryBuilder` is insecure as it does not properly use prepared statements.
It will build the query with `mt_rand`, which is used to generate [Dollar-Quoted String Constants](https://www.postgresql.org/docs/current/sql-syntax-lexical.html).
If the PRNG is broken and therefore the delimiters are calculable, you get unrestricted SQLi.

The weakness of the PRNG is introduced by a weak seed as only the current seconds are used.
This is hidden by using `microtime(true)`, where you would expect a sufficiently unknown seed, but it is a `float` in seconds.
As `mt_srand` only takes integers, the unpredictable part of the `microtime` will be truncated and only the seconds remain.

The whole `QueryBuilder` is insecure, so if it is not patched correctly it is safer to rewrite problematic queries by hand.
As the `QueryBuilder` is used throughout the applications there are many possible entry points.

#### Patch 1 - Messing/Correcting with the seed

In `common.php`: Change `mt_srand(microtime(true));` to `mt_srand(microtime(true) * 1000);`
During the CTF any other calculation done on this "seeding algorithm" will probably defend against teams.

#### Patch 2 - Mess with the AlnumGenerator
If you change the logic on how the delimiters are generated, other teams will not be able to guess them.

#### Patch 3 - Rewrite queries
Rewrite the queries using the `QueryBuilder` with simple SQL and prepared statements.

### Vuln 3 - SQLi by exploiting PDO in emulating mode

PDO-PGSQL does not care about the structure of a prepared statement when filling it with parameters.
Therefore, a non-valid prepared statement can become valid when PDO is building the query.
This can be abused in `UserDAO::getByEmailAndPassword` which is accessible with the login functionality.
The DAO uses `e?` as placeholders for the parameters of the prepared statements.
In reality PDO will only replace the question-mark with a correctly escaped string resulting in:
```
... email=e'a.valid@email.address' ...
```
This will be sent to the postgres database. There the `e` will be treated as a 
[modifier](https://www.postgresql.org/docs/14/sql-syntax-lexical.html#SQL-SYNTAX-STRINGS-ESCAPE) for the string.
This modifier activates that backslashes are used for escaping of the next character.
As PDO does not know about this, we can place a backslash at the end of a string to force the string parameter to not 
stop.
Full SQLi is gained with the second parameter, which will not be in a string context.

#### Patch 1 - Replace 'e?' with '?'

Removing all `e?` and replacing them with `?` will turn of the dangerous escape mode.

#### Patch 2 - Disable emulation

This would further harden the application, but you will still need "Patch 1" as the `e?` are invalid placeholders, so 
you have broken code.

#### Patch 3 - Add input validation

In this case you might be able to restrict the characters allowed on the login form.
If backslashes are not allowed, you are fine here.

### Vuln 4 - Session Forging

You can upload a valid PHP session file into the directory PHP is using to store the sessions. 
As the ID of the currently logged-in user is stored in the session, you can impersonate any user.

This is possible because:
1. `mkdir` is not creating directories recursively by default and silently fails.
2. `tempnam` will "silently" (with a warning) fall back to `/tmp` in case the directory it should write to does not 
exist, or cannot be written to.
3. The default PHP configuration for storing sessions is to put it into the `/tmp` folder.
4. These session files are not signed as they are treated as trusted.

There are multiple steps needed for this to work. Any of the provided patches will break the chain.

#### Patch 1 - Correctly check return flags

In `FileAnalysisMethod::run` the return type of `mkdir` is ignored.
Furthermore, the warning that is produced if a directory could not be created is hidden with `@`.
In case the directory could not be created you should just stop execution.

#### Patch 2 - Do not let tempnam fallback to /tmp

In case `tempnam` returns a `/tmp` location, just break.

#### Patch 3 - Do not expose the resulting filename

`tempnam` will generate a valid PHP session filename. 
But if the attacker does not know this filename, it cannot use the session file.
Use `file -b ...` to hide the filename from the output.

#### Patch 4 - Validate the users email correctly

Slashes which break `mkdir` should not be allowed in email addresses. 
You could also remove them before using them in the string.

#### Patch 5 - Change session configuration (php.ini)

Change the storage path `session.save_path` of the sessions somewhere else (a dedicated directory would make sense)
Implement a different session handler that does not store the sessions on disk.

CTF quick fix:
* Change the serialization mode `session.serialize_handler`
* Change how the field of the user is called in `SessionService`.

#### Patch 6 - Add a signature to the session files

Make sure that the session files cannot be tampered with outside from your application.
To prevent forging a simple signature that is checked when loading the file could let you determine, 
if it is a valid session.

### Vuln 5 - Leaking environment

In `IniAnalysisMethod::run`: `parse_ini_string` will also interpret the ini files.
You have the same capabilities as in files like `php.ini`.
So you can do basic math with bitmasks (`|`, `^`, `&`) and access environment variables with `${ENVNAME}`.
The output of the function will have the environment placeholders replaced with the content of the environment variables.
This leaks application secrets such as database credentials.

#### Patch 1 - Use parse_ini_string without fancy features

You can supply `INI_SCANNER_RAW` as a flag, which will not replace environment variables.

#### Patch 2 - Avoid parse_ini_string

You can try to implement a simple parser that does not have fancy interpretation features.


Vulnerabilities & Patches (Flag store 2)
----------------------------------------
### Vuln 6 - Simple DOM-based XSS

In the pyscript file powering the `analyze` endpoint, the `fname` variable is added to the DOM unsanitized. Trivially, something like b64 encoding `<img src=a onerror=alert(1)>` as a name for an archive will trigger an alert message, See, e.g., http://localtest.me:10010/analyze#PGltZyBzcmM9YSBvbmVycm9yPWFsZXJ0KDEpPg==@

Even if the `elog` call is removed/fixed, the regular expression used to check for tar files does a partial match due to using `re.match` instead of `re.search`:

```Python
# check if the file is a valid archive, only allow letters, numbers, underscore, and dash
# followed by standard tar suffixes
if re.match('[\w-]+\.tar((\.gz)?|(\.bz2))?', fname):
    log(f'Analyzing {fname}')
```

A possible bypass is `bar.tar.gz<img src=a onerror=alert(1)>`, like http://localtest.me:10010/analyze#YmFyLnRhci5nejxpbWcgc3JjPWEgb25lcnJvcj1hbGVydCgxKT4K@

Notice that an even stricter regexp, such as `^[\w-]+\.tar((\.gz)?|(\.bz2))?$` could be bypassed by providing a filename containing newlines, like `bar.tar.gz\n<img src=a onerror=alert(1)>` http://localtest.me:10010/analyze#YmFyLnRhci5nego8aW1nIHNyYz1hIG9uZXJyb3I9YWxlcnQoMSk+@

#### Patch

There are several ways to prevent this from working. Changing the `log` function to append textual elements filled with `innerText` is probably the most effective one.

### Vuln 7 - DOM-based XSS by shadowing Python modules via zip slip attack

It's possible to forge a tar file that, when upacked, overwrites Python modules to obtain code execution. Notice that Python code execution translates to XSS in the context of this service. The malicious tar file can be created as follows:

```Python
import tarfile
tf = tarfile.open('test.tar.gz', "w:gz")
tf.add('uuid.py', '../../lib/python3.10/uuid.py')
tf.close()
```

Where `uuid.py` is something like
```Python
from js import alert
alert("PWND")
```

Providing this file to the application triggers the XSS: http://localtest.me:10010/analyze#dGVzdC50YXIuZ3o=@H4sICGwrDWMC/3Rlc3QudGFyAO3UP0sDMRjH8Zv7KkInXZI89yeng+Dg4CTdnCM9aeTOO3I5ad+9rR0UobjUYuX7IeQJyQMhwy/aaHO78Ov7xi+bmP0Ku3eoWlsUn+vdvkhZSabW2QlMY/Jxe/2xH3km8lp1KXTNjTgn9fVV6URXNre1zDL8f1qb7WjDkxk2adW/Flqsmaaw1MPmmPl3rtxVqSv7te6V3/PvcikyZU+Z/9a/hXF1uO+n8zPN/3PsO/UyqtANfUzKt01Ms4/5Yr54fLibX/IPAAAAAAAAAAAAAAAA/GXvWrK7TwAoAAA=

#### Patch

I'm not sure if this is a bulletproof fix, but checking the tar file before unpacking it to avoid the presence of .py files seems to be a good enough solution during the CTF.

### Vuln 8 - DOM-based XSS via reflected exception message caused by unreadable files

Exceptions, or anything that prints to stderr, are *sometimes* rendered to the DOM inside the `out` div. Basically, any exception that reflects in the message part of the user-provided input can turn into an XSS. One approach is to trigger a `PermissionError` exception packing an unreadable file, as follows.

1. Create an unreadable file with permissions `000` called `<img src=fff onerror=alert(1)>`
2. Make an archive it
3. Serialize it manually and send it
4. The exception message should be printed in the page and trigger the XSS via `PermissionError: [Errno 2] Permission denied: './<img src=fff onerror=alert(1)>`

Full example:
```
$ touch '<img src=fff onerror=alert(1)>'
$ chmod 000 '<img src=fff onerror=alert(1)>'
$ sudo tar -zcvf expl.tar.gz '<img src=fff onerror=alert(1)>'
<img src=fff onerror=alert(1)>
$ echo -n 'expl.tar.gz' | base64 
ZXhwbC50YXIuZ3o=
$ cat expl.tar.gz | base64
H4sIAAAAAAAAA+3NsQrCQBCE4X2ULbW7NTnSGN/lCDkNRAN70edXCRYWahOs/q+YKXZh9sP5qMW7
Nues06V3n7xNY+/zxrYHWUVYPNua+NYvYnUVaquCRZNHxGYnGtaZ/+5a5uSqMqbbUE6f/37dAQAA
AAAAAAAAAAAAAAD4ozt4mNbVACgAAA==
```

Final URL: http://localtest.me:10010/analyze#ZXhwbC50YXIuZ3o=@H4sIAAAAAAAAA+3NsQrCQBCE4X2ULbW7NTnSGN/lCDkNRAN70edXCRYWahOs/q+YKXZh9sP5qMW7Nues06V3n7xNY+/zxrYHWUVYPNua+NYvYnUVaquCRZNHxGYnGtaZ/+5a5uSqMqbbUE6f/37dAQAAAAAAAAAAAAAAAAD4ozt4mNbVACgAAA==

#### Patch

Suppressing the exception message via a `try... Except:` construct seems to be the best option.

