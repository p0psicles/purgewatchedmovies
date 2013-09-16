# import the XBMC libraries so we can use the controls and functions of XBMC
from time import strptime, time, mktime, localtime
import os, sys, re, socket, urllib, unicodedata
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

###Remote Debugging code###
REMOTE_DBG = False 

# append pydev remote debugger
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        import pysrc.pydevd as pydevd
    # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
    except ImportError:
        sys.stderr.write("Error: " +
            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
        sys.exit(1)
### End of remote debugging

#addon id - name of addon directory
_id='script.purgewatchedmovies'
#resources directory
_resdir = "special://home/addons/" + _id + "/resources"

__addon__     = xbmcaddon.Addon()
__addonid__   = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path').decode('utf-8')
__author__    = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__language__  = __addon__.getLocalizedString
__useragent__ = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
__datapath__ = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ )
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

#get settings, not using them now, be can in the future
SETTING_alsopurgetvseries = __addon__.getSetting( "AlsoPurgeTvSeries" )
SETTING_purgexdaysback = __addon__.getSetting( "PurgexDaysBack" )

#get actioncodes from https://github.com/xbmc/xbmc/blob/master/xbmc/guilib/Key.h
ACTION_PREVIOUS_MENU = 10
ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def lognotice(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGNOTICE)

def normalize_string( text ):
    try: text = unicodedata.normalize( 'NFKD', _unicode( text ) ).encode( 'ascii', 'ignore' )
    except: pass
    return text

def setupButtons(self,x,y,w,h,a="Vert",f="",nf=""):
    self.numbut  = 0
    self.butx = x
    self.buty = y
    self.butwidth = w
    self.butheight = h
    self.butalign = a
    self.butfocus_img = f
    self.butnofocus_img = nf

def addButon(self,text):
    if self.butalign == "Hori":
        c =  xbmcgui.ControlButton(self.butx + (self.numbut * self.butwidth),self.buty,self.butwidth,self.butheight,text,self.butfocus_img,self.butnofocus_img)
        self.addControl(c)
    elif self.butalign == "Vert":
        c = xbmcgui.ControlButton(self.butx ,self.buty + (self.numbut * self.butheight),self.butwidth,self.butheight,text,self.butfocus_img,self.butnofocus_img)
        self.addControl(c)
    self.numbut += 1
    return c
    
class MyClass(xbmcgui.Window):
    def __init__(self):
        #self.addControl(xbmcgui.ControlImage(0,0,800,600, _resdir +'/Foto_Collin.png'))
        self.strActionInfo = xbmcgui.ControlLabel(100, 120, 600, 200, '', 'font13', '0xFFFF00FF')
        self.addControl(self.strActionInfo)
        self.strActionInfo.setLabel('A list of all the Movies with the status watched')
        self.list = xbmcgui.ControlList(200, 150, 800, 800, selectedColor='100')
        self.addControl(self.list)
        self.count = 0

        if not self.listmovies():
            self.close("error listing")
        self.total_movies = len(self.MovieList)
        self.MovieListTitles = []
        for movie in self.MovieList:
            current_show = {}
            self.count += 1
            log( "### %s" % movie[0] )
            current_show["moviename"] = movie[0]
            current_show["path"] = movie[1]
            current_show["art"] = movie[2]
            current_show["rating"] = movie[3]
            current_show["playcount"] = movie[4]
            current_show["lastplayed"] = movie[5]
            log(current_show["playcount"])
            
            
            self.MovieListTitles.append("Show: " + current_show["moviename"] + " | Physical Location:" + current_show["path"])
            
        self.list.addItems(self.MovieListTitles)
        self.setFocus(self.list)
        setupButtons(self,10,10,300,30,"Vert")
        self.confirm = addButon(self,"Delete All Movies from list")
        self.btn_quit = addButon(self,"Quit")

        #self.yesnomessage())
    
        
    def onControl(self, control):
        if self.list == control:
            item = self.list.getSelectedItem()
            self.message("You selected : " + item.getLabel())
        if self.confirm == control:
            self.message("Deleting all watched movies!!!")
            self.close()
        if self.btn_quit == control:
            self.close()

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()
        if action == ACTION_SELECT_ITEM:
            self.message("Debugging")

    def message(self, message):
        dialog = xbmcgui.Dialog()
        dialog.ok("You sure?",message)

    def listmovies(self):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "filter": {"field": "playcount", "operator": "greaterthan", "value": "0"}, "limits": { "start" : 0, "end": 300 }, "properties" : ["art", "rating", "thumbnail", "playcount", "file", "lastplayed"], "sort": { "order": "ascending", "method": "label", "ignorearticle": true } }, "id": "libMovies"}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log("### %s" % json_response)
        self.MovieList = []
        if json_response['result'].has_key('movies'):
            for item in json_response['result']['movies']:
                moviename = item['label']
                moviename = normalize_string( moviename )
                rating = item['rating']
                playcount = item['playcount']
                path = item['file']
                art = item['art']
                lastplayed = item['lastplayed']
                self.MovieList.append( ( moviename , path, art, rating, playcount, lastplayed ) )
        log( "### list: %s" % self.MovieList )
        return self.MovieList
        
    def yesnomessage(self):
        dialog = xbmcgui.Dialog()
        Returned = dialog.yesno("Delete these files?", "Do you want to permanently delete these files?","","","Don't remove anything","Yes delete all")
        self.message("You've selected: " + str(Returned))
        
mydisplay = MyClass()
mydisplay.doModal()

lognotice("Test Setting: " + str(SETTING_alsopurgetvseries))
del mydisplay
