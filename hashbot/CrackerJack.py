import requests
import logging
import time
import ast

from bs4 import BeautifulSoup

CJSession = {
   'id':'', 'name':'', 'state':'', 'progress':'', 'Cracked':''
    }


class CJSError(Exception):
    pass


class CJService(object):
    session = None
    url = None
    login = None
    password = None
    wrong_auth = 5

    def __init__(self, url, login, password):
        self.url = url
        self.session = requests.session();
        self.login = login
        self.password = password
        self._auth()
        logging.info("CJService was authenticated")
        
    def _post(self, url, data=None, files=None, allow_redirects=False):
        result = self.session.post(url, data, files=files, allow_redirects=allow_redirects)
        if result.status_code == 302:
            if result.headers.get("Location"):
                if "/auth/login" in result.headers.get("Location"):
                    logging.info("authentication expired")
                    self.wrong_auth -= 1
                    self._auth()
                    return self._post(url, data, files, allow_redirects)
        return result

    def _get(self, url, allow_redirects=False):
        result = self.session.get(url, allow_redirects=allow_redirects)
        if result.status_code == 302:
            if result.headers.get("Location"):
                if "/auth/login" in result.headers.get("Location"):
                    logging.info("authentication expired")
                    self.wrong_auth -= 1
                    self._auth()
                    return self._get(url, allow_redirects)
        return result
        
    def _auth(self):
        if self.wrong_auth < 0:
            raise Exception('wrong authentication') 
        result = self._get(self.url + "/auth/login")
        csrf = self._getCSRF(result.content)
        data = {'next':'', 'csrf_token':csrf, 'username':self.login, 'password':self.password}
        result = self._post(self.url + "/auth/login", data)
        self.wrong_auth = 5
        
    def _getCSRF(self, content):
        soup = BeautifulSoup(content, 'lxml')
        csrf_token = soup.find('input', {'name':'csrf_token'})['value']
        return csrf_token
    
    def getHashTypesInfo(self):
        hashinfo = "https://hashcat.net/wiki/doku.php?id=example_hashes"
        return hashinfo
    
    def getWordlists(self, session_id):
        result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/wordlist")
        soup = BeautifulSoup(result.content, 'lxml')
        files_list = soup.find('optgroup', {'label':'Files'})
        options = files_list.find_all('option')
        result = {}
        for opoption in options:
            result[opoption.attrs['value']] = opoption.text
        return result
    
    def getSessions(self):
        sess = []
        result = self._get(self.url)
        if result.status_code == 302:
            raise Exception('wrong authentication')
        soup = BeautifulSoup(result.content, 'lxml')
        table = soup.find('table')
        if not table:
            return sess
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            if len(cols) == 8:
                sess.append({'id':cols[0], 'name':cols[2], 'state':cols[3], 'progress':cols[4], 'Cracked':cols[5]})
            else:
                sess.append({'id':cols[0], 'name':cols[1], 'state':cols[2], 'progress':cols[3], 'Cracked':cols[4]})
        return sess
    
    def getSessionWithID(self, id):
        sess = self.getSessions()
        for s in sess:
            if s['id'] == id:
                return s 
        return None

    def getSessionByName(self, name):
        for s in self.getSessions():
            if s['name'] == name:
                return s 
            
    def setStopDate(self, session_id):
        result = self._get(self.url + "/sessions/" + str(session_id) + "/settings")
        csrf = self._getCSRF(result.content)
        data = {'csrf_token':csrf, 'termination_date':'2030-08-09', 'termination_time':'11:35'}
        result = self._post(self.url + "/sessions/" + str(session_id) + "/settings/save", data=data, allow_redirects=False)
        if result.status_code == 302:
            return True
        else:
            return False
    
    def createSession(self, name):
        result = self._get(self.url)
        csrf = self._getCSRF(result.content)
        data = {'csrf_token':csrf, 'description':name}
        result = self._post(self.url + "/sessions/create", data=data, allow_redirects=False)
        if result.status_code == 302:
            ses_id = result.headers['Location']
            ses_id = ses_id.replace(self.url + "/sessions/", '')
            ses_id = ses_id.replace("/setup/hashes", '')
            self.setStopDate(ses_id)
            return ses_id
        else:
            return None

    def deleteSession(self, session_id): 
        result = self._get(self.url, allow_redirects=False)
        if (result.status_code == 302):
            raise Exception('wrong authentication')
        csrf = self._getCSRF(result.content)
        data = {'csrf_token':csrf}
        result = self._post(self.url + "/sessions/" + str(session_id) + "/delete", data=data, allow_redirects=False)
        if result.status_code == 302:
            return True
        else:
            return False

    def getHashTypes(self, session_id):
        hash_type = {}
        possible = []
        result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/hashcat")
        csrf = self._getCSRF(result.content)
        soup = BeautifulSoup(result.content, 'lxml')
        js = soup.find_all('script')
        for script in js:
                if (len(script.contents)) > 0:
                    content = str(script.contents[0])
                    if "supported_hashes" in content:
                        tmp = content.split(" = ", 1)
                        part = tmp[1].split(";", 1)[0]
                        hash_type = ast.literal_eval(part)
        if "Possible Hash Type:" in result.text:
            soup = BeautifulSoup(result.content, 'lxml')
            alert = soup.find('div', {'class':'alert alert-primary'})
            ul = alert.find('ul')
            lines = ul.find_all('li')
            for l in lines:
                possible.append(l.text)
        return hash_type, possible
    
    def setUPhash(self, session_id, hash_data): 
            result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/hashes")
            csrf = self._getCSRF(result.content)
            data = {'csrf_token': (None, csrf), 'mode':(None, "1"), 'hashes':(None, hash_data)}  
            result = self._post(self.url + "/sessions/" + str(session_id) + "/setup/hashes/save", files=data, allow_redirects=False)
            if result.status_code == 302:
                return True
            else:
                return False  
    def setUPhashFile(self, session_id, filename, data): 
            result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/hashes")
            csrf = self._getCSRF(result.content)
            data = {'csrf_token': (None, csrf), 'mode':(None, "0"), 'hashfile':(filename, data,'application/octet-stream')}  
            result = self._post(self.url + "/sessions/" + str(session_id) + "/setup/hashes/save", files=data, allow_redirects=False)
            if result.status_code == 302:
                return True
            else:
                return False              
    def setHashTypeAndAttakModeWordlist(self, session_id, hash_type): 
            result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/hashcat")
            csrf = self._getCSRF(result.content)
            data = {'csrf_token': (None, csrf), 'hash-type':(None, str(hash_type)), 'workload':(None, "2"), 'mode':(None, "0")} 
            result = self._post(self.url + "/sessions/" + str(session_id) + "/setup/hashcat/save", files=data, allow_redirects=False)
            if result.status_code == 302:
                return True
            else:
                return False
    
    def setHashTypeAndAttakModeMask(self, session_id, hash_type): 
            result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/hashcat")
            csrf = self._getCSRF(result.content)
            data = {'csrf_token': (None, csrf), 'hash-type':(None, str(hash_type)), 'workload':(None, "2"), 'mode':(None, "3")} 
            result = self._post(self.url + "/sessions/" + str(session_id) + "/setup/hashcat/save", files=data, allow_redirects=False)
            if result.status_code == 302:
                return True
            else:
                return False
    
    def setWordList(self, session_id, wordlist):
            result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/wordlist")
            csrf = self._getCSRF(result.content)
            data = {'csrf_token': (None, csrf), 'wordlist_type':(None, "0"), 'wordlist':(None, wordlist)} 
            result = self._post(self.url + "/sessions/" + str(session_id) + "/setup/wordlist/save", files=data, allow_redirects=False)
            if result.status_code == 302:
                return True
            else:
                return False 
        
    def _sendAction(self, session_id, action):
            result = self._get(self.url + "/sessions/" + str(session_id) + "/view")    
            if "Missing Configuration" in str(result.content):
                soup = BeautifulSoup(result.content, 'lxml')
                wrongConfig = soup.find('button', {'class':'btn btn-warning'})
                if wrongConfig != None:
                    warn = wrongConfig.attrs['data-content']
                    warn = warn.replace("<br>", "\n")
                    return  warn
            else:
                csrf = self._getCSRF(result.content)
                data = {'csrf_token': (None, csrf), 'action':(None, action)} 
                result = self._post(self.url + "/sessions/" + str(session_id) + "/action", data=data, allow_redirects=False)
                return None

    def pauseSession(self, session_id):
        return self._sendAction(session_id, "pause")    
    
    def startSession(self, session_id):
        return self._sendAction(session_id, "start")    
    
    def resumeSession(self, session_id):
        return self._sendAction(session_id, "resume")  
    
    def stopSession(self, session_id):
        return self._sendAction(session_id, "stop")  
    
    def restoreSession(self, session_id):
        return self._sendAction(session_id, "restore") 
    
    def _downloadFile(self, session_id, filename):
        result = self._get(self.url + "/sessions/" + str(session_id) + "/files")
        csrf = self._getCSRF(result.content)
        data = {'csrf_token': (None, csrf)} 
        result = self._post(self.url + "/sessions/" + str(session_id) + "/download/" + filename, data=data, allow_redirects=False)
        return result.content

    def getResult(self, session_id):
        return self._downloadFile(session_id, "hashes.cracked")
            
    def getFiles(self, session_id):
        result = self._get(self.url + "/sessions/" + str(session_id) + "/files")
        soup = BeautifulSoup(result.content, 'lxml')
        table = soup.find('table')
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')
        files = []
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            files.append(cols[0])
        return files
    
    def setMask(self, session_id, mask):
        result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/mask")
        csrf = self._getCSRF(result.content)
        count = mask.count("?")
        data = {'csrf_token': (None, csrf),'mask_type':(None,str(2)), 'compiled-mask':(None, mask), 'mask-max-characters':(None, str(count))} 
        result = self._post(self.url + "/sessions/" + str(session_id) + "/setup/mask/save", data=data, allow_redirects=False)
        if result.status_code == 302:
                return True
        else:
                return False 
            
    def setMaskWithIncrement(self, session_id, mask,minlen=1,maxlen=9):
        result = self._get(self.url + "/sessions/" + str(session_id) + "/setup/mask")
        csrf = self._getCSRF(result.content)
        data = {'csrf_token': (None, csrf),'enable_increments':(None,"1"),'mask_type':(None,str(2)),'increment-min':(None,str(minlen)), 'increment-max':(None,str(maxlen)),  'compiled-mask':(None, mask), 'mask-max-characters':(None, str(maxlen))} 
        result = self._post(self.url + "/sessions/" + str(session_id) + "/setup/mask/save", data=data, allow_redirects=False)
        if result.status_code == 302:
                return True
        else:
                return False             
