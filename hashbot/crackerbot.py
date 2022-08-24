import telebot
import logging
from telebot import types
from telebot import apihelper
import numpy


class CracerBotService(object):
    BOT_VERSION = "0.7b"
    STATE_FREE = 'STATE_FREE'
    STATE_CREATE_TASK_NAME = 'STATE_CREATE_TASK_NAME'
    STATE_CREATE_TASK_HASH = 'STATE_CREATE_TASK_HASH'
    STATE_CREATE_TASK_HASH_TYPE = 'STATE_CREATE_TASK_HASH_TYPE'
    STATE_CREATE_TASK_BRUT_TYPE = 'STATE_CREATE_TASK_BRUT_TYPE'
    STATE_CREATE_TASK_BRUT_WORDLIST = 'STATE_CREATE_TASK_BRUT_WORDLIST'
    STATE_CREATE_TASK_BRUT_MASK = 'STATE_CREATE_TASK_BRUT_MASK'
    STATE_CREATE_TASK_BRUT_MASK_INCREMENT = 'STATE_CREATE_TASK_BRUT_MASK_INCREMENT'
    STATE_DELETE_TASK = 'STATE_DELETE_TASK'
    apihelper.ENABLE_MIDDLEWARE = True
    
    SESSIONS = {
        -1: {
            'state': STATE_FREE
        }
    }
    all_hash_types = None
    markup = None
    AvailableUsers = []
    cjs = None
    telegramBot = None
    
    def __init__(self, cjservice, bot_token, proxy_host=None, proxy_port=None):
        self.cjs = cjservice
        self.telegramBot = telebot.TeleBot(bot_token)
        if proxy_host != None:
            if proxy_port != None:
                apihelper.proxy = {'https':'socks5h://' + proxy_host + ':' + proxy_port}
        self.markup = types.ReplyKeyboardMarkup()
        itembtcreate = types.KeyboardButton('/create task')
        itembtshow = types.KeyboardButton('/show tasks')
        itembtinfo = types.KeyboardButton('/info')
        self.markup.row(itembtcreate, itembtshow, itembtinfo)
        self.markup.resize_keyboard = True
        # like decorators
        self.telegramBot.add_middleware_handler(self.set_session, update_types=['message'])
        # like decorators
        handler_dict = self.telegramBot._build_handler_dict(self.callback_worker, func=lambda call: True)
        self.telegramBot.add_callback_query_handler(handler_dict)
        # like decorators
        handler_dict = self.telegramBot._build_handler_dict(self.response_all, content_types=["text"])
        self.telegramBot.add_message_handler(handler_dict)
        handler_dict = self.telegramBot._build_handler_dict(self.response_for_documents, content_types=["document"])
        self.telegramBot.add_message_handler(handler_dict)
    
    def start(self):
        self.telegramBot.polling(none_stop=True, interval=0)
        
    def addAvailableUser(self, user_id):
        self.AvailableUsers.append(user_id)
    
    def getMaskLen(self, mask):
        count = mask.count("?")
        return count
    
    def response_for_documents(self,message):
        self.log(message, str(self.telegramBot.session))
        if  self.telegramBot.session == None:
            self.telegramBot.send_message(message.chat.id, "you don't have permissions")
            return
        state = self.telegramBot.session['state']
        if state == None: 
            return
        if message.document == None:
            return
        if self.telegramBot.session['state'] == self.STATE_CREATE_TASK_HASH:
            file_info = self.telegramBot.get_file(message.document.file_id)
            downloaded_file = self.telegramBot.download_file(file_info.file_path)
            if (len(downloaded_file) < 1):
                self.telegramBot.session['state'] = self.STATE_FREE
                self.telegramBot.send_message(message.chat.id, "what do you want?", reply_markup=self.markup)
            else:
                self.telegramBot.session['hash'] = message.document.file_name
                self.telegramBot.session['state'] = self.STATE_CREATE_TASK_HASH_TYPE
                self.cjs.setUPhashFile(self.telegramBot.session['task_id'],message.document.file_name,downloaded_file)
                _hash_types, possible = self.cjs.getHashTypes(self.telegramBot.session['task_id'])
                self.telegramBot.all_hash_types = _hash_types
                if (len(possible) > 0):
                    self.telegramBot.send_message(message.chat.id, "Possible types")
                    self.telegramBot.send_message(message.chat.id, str(possible))
                self.telegramBot.send_message(message.chat.id, "enter hash type:")
            return
        
    def get_or_create_session(self, user_id):
        if user_id in self.AvailableUsers:
            try:
                return self.SESSIONS[user_id]
            except KeyError:
                self.SESSIONS[user_id] = {'state': self.STATE_FREE}
                return self.SESSIONS[user_id]
        else:
            logging.info("Unknown user: " + str(user_id)) 
            
    def log(self, message, text):
        name = str(message.from_user.username) + ":" + str(message.from_user.id)
        logging.info(name + " - " + text)
        
    def set_session(self, bot_instance, message):
        bot_instance.session = self.get_or_create_session(message.from_user.username)
    
    def doCommand(self, message): 
        if(message.text.startswith("/start")):
            self.telegramBot.session['state'] = self.STATE_FREE
            self.telegramBot.send_message(message.chat.id, "what do you want?", reply_markup=self.markup)
        elif(message.text.startswith("/show")):
            self.telegramBot.session['state'] = self.STATE_FREE
            self.send_all_sessions(message)
        elif(message.text.startswith("/create")):
            self.telegramBot.session['state'] = self.STATE_CREATE_TASK_NAME
            self.telegramBot.send_message(message.chat.id, "enter task name:")
        elif(message.text.startswith("/info")):
            htp = self.cjs.getHashTypesInfo()
            self.telegramBot.send_message(message.chat.id, "BOT VERSION: " + self.BOT_VERSION + "\nHash types: https://hashcat.net/wiki/doku.php?id=example_hashes" + "\n" + "Mask format: https://hashcat.net/wiki/doku.php?id=mask_attack", reply_markup=self.markup)

    def send_all_sessions(self, message):
        sessionList = self.cjs.getSessions()
        if (len(sessionList) < 1):
            self.telegramBot.send_message(message.chat.id, "no tasks")
        else:
            sessionsToSend = numpy.array_split(sessionList, int((len(sessionList)/10))+1)
            keyboard = types.InlineKeyboardMarkup()
            for partSessionList in sessionsToSend:
                for sess in partSessionList:
                    b = types.InlineKeyboardButton(sess["name"] + "   [" + sess["state"] + "]", callback_data="task_info" + "$" + str(sess["id"]))
                    keyboard.add(b)
                self.telegramBot.send_message(message.chat.id, "select task", reply_markup=keyboard)

    def callback_worker(self, call):
        self.log(call.message, str(call.data))
        if  self.telegramBot.session == None:
            self.telegramBot.send_message(call.message.chat.id, "you don't have permissions")
            return
        itembt_get=None
        state = self.telegramBot.session['state']
        if state == None: 
            return
        if  "task_info" in call.data:
            m, sess_id = call.data.split("$")
            s = self.cjs.getSessionWithID(sess_id)
            keyboard = types.InlineKeyboardMarkup()
            if s['Cracked']:
                if s['Cracked'].split("/")[0]!="0":
                        itembt_get = types.InlineKeyboardButton('result', callback_data="task_result" + "$" + str(sess_id))
            if s['state'] == "Cracked":
                itembt_get = types.InlineKeyboardButton('result', callback_data="task_result" + "$" + str(sess_id))
                itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(sess_id))
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(sess_id))
                keyboard.row(itembt_get, itembtdelete)
                keyboard.row(itembtdstatus)
            if s['state'] == "Error":
                itembt_download = types.InlineKeyboardButton('log', callback_data="task_getlog" + "$" + str(sess_id))
                itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(sess_id))
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(sess_id))
                keyboard.row(itembt_download, itembtdelete)
                if itembt_get:
                    keyboard.row(itembt_get,itembtdstatus)
                else:
                    keyboard.row(itembtdstatus)                    
            if s['state'] == "Not Started":
                itembtstart = types.InlineKeyboardButton('start', callback_data="task_start" + "$" + str(sess_id))
                itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(sess_id))
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(sess_id))
                keyboard.row(itembtstart, itembtdelete)
                if itembt_get:
                    keyboard.row(itembt_get,itembtdstatus)
                else:
                    keyboard.row(itembtdstatus) 
            if s['state'] == "Running":
                itembtstop = types.InlineKeyboardButton('stop', callback_data="task_stop" + "$" + str(sess_id))
                itembtpause = types.InlineKeyboardButton('pause', callback_data="task_pause" + "$" + str(sess_id))
                itembt_download = types.InlineKeyboardButton('log', callback_data="task_getlog" + "$" + str(sess_id))
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(sess_id))
                keyboard.row(itembtpause, itembtstop, itembt_download)
                if itembt_get:
                    keyboard.row(itembt_get,itembtdstatus)
                else:
                    keyboard.row(itembtdstatus)
            if s['state'] == "Paused":
                itembtresume = types.InlineKeyboardButton('resume', callback_data="task_resume" + "$" + str(sess_id))
                itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(sess_id))
                itembt_download = types.InlineKeyboardButton('log', callback_data="task_getlog" + "$" + str(sess_id))
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(sess_id))
                keyboard.row(itembtresume, itembtdelete)
                if itembt_get:
                    keyboard.row(itembt_get,itembt_download, itembtdstatus)
                else:
                    keyboard.row(itembt_download, itembtdstatus)
            if s['state'] == "Stopped":
                itembt_start = types.InlineKeyboardButton('start', callback_data="task_start" + "$" + str(sess_id))
                itembt_resume = types.InlineKeyboardButton('restore', callback_data="task_restore" + "$" + str(sess_id))
                itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(sess_id))
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(sess_id))
                itembt_download = types.InlineKeyboardButton('log', callback_data="task_getlog" + "$" + str(sess_id))
                keyboard.row(itembt_start, itembt_resume, itembtdelete)
                if itembt_get:
                    keyboard.row(itembt_get,itembt_download, itembtdstatus)
                else:
                    keyboard.row(itembt_download, itembtdstatus)
            if s['state'] == "Finished":
                itembt_download = types.InlineKeyboardButton('log', callback_data="task_getlog" + "$" + str(sess_id))
                itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(sess_id))
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(sess_id))
                keyboard.row(itembt_download, itembtdelete)
                if itembt_get:
                    keyboard.row(itembt_get,itembtdstatus)
                else:
                    keyboard.row(itembtdstatus)
            keyboard.resize_keyboard = True
            self.telegramBot.send_message(call.message.chat.id, str(s), reply_markup=keyboard)
        if "task_getlog" in call.data:
            m, sess_id = call.data.split("$")
            files = self.cjs.getFiles(sess_id)
            for  fl in files:
                if "screen.log" in fl:
                    self.telegramBot.send_document(chat_id=call.message.chat.id, data=self.cjs._downloadFile(sess_id, fl), caption=fl, visible_file_name=fl)
        if "task_result" in call.data:
            m, sess_id = call.data.split("$")
            s = self.cjs.getSessionWithID(sess_id)
            result = self.cjs.getResult(sess_id)
            if len(result)>200:
                self.telegramBot.send_document(chat_id=call.message.chat.id, data=result, caption=(s["name"]+".txt"), visible_file_name=(s["name"]+".txt"))
            else:
                self.telegramBot.send_message(call.message.chat.id, result)
        if "task_start" in call.data:
            m, sess_id = call.data.split("$")
            result = self.cjs.startSession(sess_id)
            if result != None:
                self.telegramBot.send_message(call.message.chat.id, result)
            else:
                self.telegramBot.send_message(call.message.chat.id, "task will be started")
        if "task_stop" in call.data:
            m, sess_id = call.data.split("$")
            result = self.cjs.stopSession(sess_id)
            if result != None:
                self.telegramBot.send_message(call.message.chat.id, result)
            else:
                self.telegramBot.send_message(call.message.chat.id, "task will be stopped")
        if "task_resume" in call.data:
            m, sess_id = call.data.split("$")
            result = self.cjs.resumeSession(sess_id)
            if result != None:
                self.telegramBot.send_message(call.message.chat.id, result)
            else:
                self.telegramBot.send_message(call.message.chat.id, "task will be resumed")
        if "task_restore" in call.data:
            m, sess_id = call.data.split("$")
            result = self.cjs.restoreSession(sess_id)
            if result != None:
                self.telegramBot.send_message(call.message.chat.id, result)
            else:
                self.telegramBot.send_message(call.message.chat.id, "task will be restored")
        if "task_pause" in call.data:
            m, sess_id = call.data.split("$")
            result = self.cjs.pauseSession(sess_id)
            if result != None:
                self.telegramBot.send_message(call.message.chat.id, result)
            else:
                self.telegramBot.send_message(call.message.chat.id, "task will be paused")
        if "task_delete" in call.data:
            m, sess_id = call.data.split("$")
            keyboard = types.InlineKeyboardMarkup()
            itembtyes = types.InlineKeyboardButton('YES', callback_data="task_yes_delete" + "$" + str(sess_id))
            itembtno = types.InlineKeyboardButton('NO', callback_data="task_no_delete" + "$" + str(sess_id))
            keyboard.row(itembtyes, itembtno)
            self.telegramBot.session['state'] = self.STATE_DELETE_TASK
            keyboard.resize_keyboard = True
            self.telegramBot.send_message(call.message.chat.id, "You really want to remove task with id " + str(sess_id), reply_markup=keyboard)
        if "task_yes_delete" in call.data:
            if self.telegramBot.session['state'] == self.STATE_DELETE_TASK:
                m, sess_id = call.data.split("$")
                self.cjs.deleteSession(sess_id)
                self.telegramBot.send_message(call.message.chat.id, "Task " + str(sess_id) + " will be deleted")
        if "task_no_delete" in call.data:
            self.telegramBot.session['state'] = self.STATE_FREE
            self.telegramBot.send_message(call.message.chat.id, "what do you want?", reply_markup=self.markup)
        if "task_wordlist" in call.data:
            m, sess_id, wordlist = call.data.split("$")
            self.cjs.setWordList(sess_id, wordlist)
            s = self.cjs.getSessionWithID(sess_id)
            keyboard = types.InlineKeyboardMarkup()
            itembtstart = types.InlineKeyboardButton('start', callback_data="task_start" + "$" + str(sess_id))
            itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(sess_id))
            keyboard.row(itembtstart, itembtdelete)
            itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(sess_id))
            keyboard.row(itembtdstatus)
            keyboard.resize_keyboard = True
            self.telegramBot.send_message(call.message.chat.id, str(s), reply_markup=keyboard)
            
    def response_all(self, message):
        self.log(message, str(self.telegramBot.session))
        if  self.telegramBot.session == None:
            self.telegramBot.send_message(message.chat.id, "you don't have permissions")
            return
        state = self.telegramBot.session['state']
        if state == None: 
            return
        if str(message.text).startswith("/"):
            self.doCommand(message)
            return
        if self.telegramBot.session['state'] == self.STATE_CREATE_TASK_NAME:
            taskname = message.text
            self.telegramBot.session['task_name'] = taskname
            ses_id = self.cjs.createSession(taskname)
            self.telegramBot.session['task_id'] = ses_id
            self.telegramBot.send_message(message.chat.id, "enter hash:")
            self.telegramBot.session['state'] = self.STATE_CREATE_TASK_HASH
            return
        if self.telegramBot.session['state'] == self.STATE_CREATE_TASK_HASH:
            hash_text = message.text
            if (len(hash_text) < 6):
                self.telegramBot.session['state'] = self.STATE_FREE
                self.telegramBot.send_message(message.chat.id, "what do you want?", reply_markup=self.markup)
            else:
                self.telegramBot.session['hash'] = hash_text
                self.telegramBot.session['state'] = self.STATE_CREATE_TASK_HASH_TYPE
                self.cjs.setUPhash(self.telegramBot.session['task_id'], self.telegramBot.session['hash'])
                _hash_types, possible = self.cjs.getHashTypes(self.telegramBot.session['task_id'])
                self.telegramBot.all_hash_types = _hash_types
                if (len(possible) > 0):
                    self.telegramBot.send_message(message.chat.id, "Possible types")
                    self.telegramBot.send_message(message.chat.id, str(possible))
                self.telegramBot.send_message(message.chat.id, "enter hash type:")
            return
        if self.telegramBot.session['state'] == self.STATE_CREATE_TASK_HASH_TYPE:
            hash_type = message.text
            try:
                hash_type_number = int (hash_type)
                if self.telegramBot.all_hash_types != None:
                    if self.telegramBot.all_hash_types[hash_type] == None:
                        raise Exception('wrong hash type')
                self.telegramBot.session['hash_type'] = hash_type_number
                mess = '''Enter brute force type:
 1 - wordlist
 2 - custom mask
 3 - all char, length from 1 to 9 
 4 - low & uppeer case & digest from 1 to 9
 '''
                self.telegramBot.send_message(message.chat.id, mess)
                self.telegramBot.session['state'] = self.STATE_CREATE_TASK_BRUT_TYPE          
            except:
                self.telegramBot.send_message(message.chat.id, "wrong hash type!")
                self.telegramBot.send_message(message.chat.id, "what do you want?", reply_markup=self.markup)
                self.telegramBot.session['state'] = self.STATE_FREE
            return
        if self.telegramBot.session['state'] == self.STATE_CREATE_TASK_BRUT_TYPE:
            brut_type = message.text
            try:
                tp = int(brut_type)
                if tp > 4 or tp < 1:
                    mess = '''Enter brut type:
 1 - wordlist
 2 - custom mask
 3 - all char, length from 1 to 9 
 4 - low & uppeer case & digest from 1 to 9
 '''
                    self.telegramBot.send_message(message.chat.id, mess)
                    return
                else:
                    if tp == 1:
                        self.cjs.setHashTypeAndAttakModeWordlist(self.telegramBot.session['task_id'], self.telegramBot.session['hash_type'])
                        self.telegramBot.session['state'] == self.STATE_CREATE_TASK_BRUT_WORDLIST
                        wordlists = self.cjs.getWordlists(self.telegramBot.session['task_id'])
                        keyboard = types.InlineKeyboardMarkup()
                        wlNames = wordlists.keys()
                        for wnls in wlNames:
                            wordlists[wnls]
                            button = types.InlineKeyboardButton(wordlists[wnls], callback_data="task_wordlist" + "$" + str(self.telegramBot.session['task_id']) + "$" + wnls)
                            keyboard.row(button)
                        keyboard.resize_keyboard = True
                        self.telegramBot.send_message(message.chat.id, "Which word list to use?" , reply_markup=keyboard)
                    elif tp == 2:
                        self.cjs.setHashTypeAndAttakModeMask(self.telegramBot.session['task_id'], self.telegramBot.session['hash_type'])
                        self.telegramBot.session['state'] = self.STATE_CREATE_TASK_BRUT_MASK
                        self.telegramBot.send_message(message.chat.id, "enter mask (?a?a?a...)\n\
example: -1 ?d?l?u ?1?1?1?1?1?1?1?1\n\
example: -1 ?a -2 ?l   ?1?2\n\
example:    ?a?a?a?a?a?")
                    elif tp == 3:
                        self.telegramBot.session['mask']="?a?a?a?a?a?a?a?a?a"
                        self.cjs.setHashTypeAndAttakModeMask(self.telegramBot.session['task_id'], self.telegramBot.session['hash_type'])
                        self.cjs.setMaskWithIncrement(self.telegramBot.session['task_id'] ,self.telegramBot.session['mask'], minlen=1, maxlen=9)
                        keyboard = types.InlineKeyboardMarkup()
                        itembtstart = types.InlineKeyboardButton('start', callback_data="task_start" + "$" + str(self.telegramBot.session['task_id']))
                        itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(self.telegramBot.session['task_id']))
                        keyboard.row(itembtstart, itembtdelete)
                        itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(self.telegramBot.session['task_id']))
                        keyboard.row(itembtdstatus)
                        keyboard.resize_keyboard = True
                        self.telegramBot.send_message(message.chat.id, self.telegramBot.session['mask'] + " mask was saved", reply_markup=keyboard)
                        self.telegramBot.session['state'] = self.STATE_FREE
                    elif tp == 4:
                        self.telegramBot.session['mask']="-1 ?l?u?d ?1?1?1?1?1?1?1?1?1"
                        self.cjs.setHashTypeAndAttakModeMask(self.telegramBot.session['task_id'], self.telegramBot.session['hash_type'])
                        self.cjs.setMaskWithIncrement(self.telegramBot.session['task_id'] ,self.telegramBot.session['mask'], minlen=1, maxlen=9)
                        keyboard = types.InlineKeyboardMarkup()
                        itembtstart = types.InlineKeyboardButton('start', callback_data="task_start" + "$" + str(self.telegramBot.session['task_id']))
                        itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(self.telegramBot.session['task_id']))
                        keyboard.row(itembtstart, itembtdelete)
                        itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(self.telegramBot.session['task_id']))
                        keyboard.row(itembtdstatus)
                        keyboard.resize_keyboard = True
                        self.telegramBot.send_message(message.chat.id, self.telegramBot.session['mask'] + " mask was saved", reply_markup=keyboard)
                        self.telegramBot.session['state'] = self.STATE_FREE
            except:
                pass
            return
        if self.telegramBot.session['state'] == self.STATE_CREATE_TASK_BRUT_MASK:
            mask = message.text
            if mask:
                self.telegramBot.session['mask'] = mask
                self.telegramBot.session['state'] = self.STATE_CREATE_TASK_BRUT_MASK_INCREMENT
                self.telegramBot.send_message(message.chat.id, "mask was saved")
                self.telegramBot.send_message(message.chat.id, "enter max increment (0 for disable):")
                return
        if self.telegramBot.session['state'] == self.STATE_CREATE_TASK_BRUT_MASK_INCREMENT:
            incriment = None
            try:
                incriment = abs(int(message.text))
            except:
                self.telegramBot.send_message(message.chat.id, "wrong number")
                self.telegramBot.session['state'] = self.STATE_FREE
                return
            if incriment == 0:
                self.cjs.setMask(self.telegramBot.session['task_id'] , self.telegramBot.session['mask'])
                keyboard = types.InlineKeyboardMarkup()
                itembtstart = types.InlineKeyboardButton('start', callback_data="task_start" + "$" + str(self.telegramBot.session['task_id']))
                itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(self.telegramBot.session['task_id']))
                keyboard.row(itembtstart, itembtdelete)
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(self.telegramBot.session['task_id']))
                keyboard.row(itembtdstatus)
                keyboard.resize_keyboard = True
                self.telegramBot.send_message(message.chat.id, self.telegramBot.session['mask'] + " mask was saved", reply_markup=keyboard)
            elif incriment > 0:
                self.cjs.setMaskWithIncrement(self.telegramBot.session['task_id'] , self.telegramBot.session['mask'], minlen=1, maxlen=incriment)
                keyboard = types.InlineKeyboardMarkup()
                itembtstart = types.InlineKeyboardButton('start', callback_data="task_start" + "$" + str(self.telegramBot.session['task_id']))
                itembtdelete = types.InlineKeyboardButton('delete', callback_data="task_delete" + "$" + str(self.telegramBot.session['task_id']))
                keyboard.row(itembtstart, itembtdelete)
                itembtdstatus = types.InlineKeyboardButton('status', callback_data="task_info" + "$" + str(self.telegramBot.session['task_id']))
                keyboard.row(itembtdstatus)
                keyboard.resize_keyboard = True
                self.telegramBot.send_message(message.chat.id, self.telegramBot.session['mask'] + " with increment (" + str(incriment) + ") mask was saved", reply_markup=keyboard)
            self.telegramBot.session['state'] = self.STATE_FREE 
            return
        self.telegramBot.send_message(message.chat.id, "what do you want?", reply_markup=self.markup)
