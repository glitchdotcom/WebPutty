import urllib
import urllib2

from BeautifulSoup import BeautifulSoup, CData

class FogBugzAPIError(Exception):
    pass

class FogBugzLogonError(FogBugzAPIError):
    pass

class FogBugzConnectionError(FogBugzAPIError):
    pass

class FogBugz:
    def __init__(self, url, token=None):
        self.__handlerCache = {}
        if not url.endswith('/'):
            url += '/'

        if token:
            self._token =  token.encode('utf-8')
        else:
            self_token = None

        self._opener = urllib2.build_opener()
        try:
            soup = BeautifulSoup(self._opener.open(url + 'api.xml'))
        except urllib2.URLError:
            raise FogBugzConnectionError("Library could not connect to the FogBugz API.  Either this installation of FogBugz does not support the API, or the url, %s, is incorrect." % (self._url,))
        self._url = url + soup.response.url.string
        self.currentFilter = None

    def logon(self, username, password):
        """
        Logs the user on to FogBugz.

        Returns None for a successful login.
        """
        if self._token:
            self.logoff()
        try:
            response = self.__makerequest('logon', email=username, password=password)
        except FogBugzAPIError, e:
            raise FogBugzLogonError(e)
        
        self._token = response.token.string
        if type(self._token) == CData:
                self._token = self._token.encode('utf-8')
        
    def logoff(self):
        """
        Logs off the current user.
        """
        self.__makerequest('logoff')
        self._token = None

    def token(self,token):
        """
        Set the token without actually logging on.  More secure.
        """
        self._token = token.encode('utf-8')

    def __makerequest(self, cmd, **kwargs):
        kwargs["cmd"] = cmd
        if self._token:
            kwargs["token"] = self._token

        try:
            response = BeautifulSoup(self._opener.open(self._url+urllib.urlencode(dict([k, v.encode('utf-8') if isinstance(v,basestring) else v ] for k, v in kwargs.items())))).response
        except urllib2.URLError, e:
            raise FogBugzConnectionError(e)
        except UnicodeDecodeError, e:
            print kwargs
            raise

        if response.error:
            raise FogBugzAPIError('Error Code %s: %s' % (response.error['code'], response.error.string,))
        return response

    def __getattr__(self, name):
        """
        Handle all FogBugz API calls.

        >>> fb.logon(email@example.com, password)
        >>> response = fb.search(q="assignedto:email")
        """

        # Let's leave the private stuff to Python
        if name.startswith("__"):
            raise AttributeError("No such attribute '%s'" % name)

        if not self.__handlerCache.has_key(name):
            def handler(**kwargs):
                return self.__makerequest(name, **kwargs)
            self.__handlerCache[name] = handler
        return self.__handlerCache[name]


