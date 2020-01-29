# goopy Utility Routines
A body of code to use Google APIs more conveniently.
## keep.py
Implements the KeepSession class. On instantiation, a configuration file is read from ~/google.ini.  This determines the Google ID to use and the location to maintain a cache for local persistence of session data.  If instantiated with the unpickle=True argument, a session token will be used if available so that login need not be repeated, and the token will be stored in cache along with additioanl session data for reuse by later instantiations.

### Methods
The getClient() method returns the keep object used by the gkeepapi package for all operations on notes.
## people.py
An intermediate layer for using the Google API to access and manipulate Google Contact data.

Documentation TBD
