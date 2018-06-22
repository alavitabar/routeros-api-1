import sys, binascii, socket, hashlib, ssl

class Api:
    "Routeros api"
    def __init__(self, host, port, usessl=False, sslverify=True, debug=False):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if usessl:
            context = ssl.SSLContext()
            if sslverify:
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = True
                context.load_default_certs()
            ws = context.wrap_socket(s, server_hostname=host)
        else:
            ws = s
        ws.connect((host,port))
        self.connection = ws
        self.currenttag = 0
        self.debug = debug
        self._logged = False
 
    def _talk(self, words):
        if self._writeSentence(words) == 0: return
        r = []
        while 1:
            i = self._readSentence();
            if len(i) == 0: continue
            reply = i[0]
            attrs = {}
            for w in i[1:]:
                j = w.find('=', 1)
                if (j == -1):
                    attrs[w] = ''
                else:
                    attrs[w[:j]] = w[j+1:]
            r.append((reply, attrs))
            if reply == '!done': return r

    def _writeSentence(self, words):
        ret = 0
        for w in words:
            self._writeWord(w)
            ret += 1
        self._writeWord('')
        return ret

    def _readSentence(self):
        r = []
        while 1:
            w = self._readWord()
            if w == '': return r
            r.append(w)
            
    def _writeWord(self, w):
        if self.debug:
            print(("<<< " + w))
        self._writeLen(len(w))
        self._writeStr(w)

    def _readWord(self):
        ret = self._readStr(self._readLen())
        if self.debug:
            print((">>> " + ret))
        return ret

    def _writeLen(self, l):
        if l < 0x80:
            self._writeByte((l).to_bytes(1, sys.byteorder))
        elif l < 0x4000:
            l |= 0x8000
            tmp = (l >> 8) & 0xFF
            self._writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
        elif l < 0x200000:
            l |= 0xC00000
            self._writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
        elif l < 0x10000000:        
            l |= 0xE0000000         
            self._writeByte(((l >> 24) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
        else:                       
            self._writeByte((0xF0).to_bytes(1, sys.byteorder))
            self._writeByte(((l >> 24) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
            self._writeByte((l & 0xFF).to_bytes(1, sys.byteorder))

    def _readLen(self):              
        c = ord(self._readStr(1))    
        if (c & 0x80) == 0x00:      
            pass                    
        elif (c & 0xC0) == 0x80:    
            c &= ~0xC0              
            c <<= 8                 
            c += ord(self._readStr(1))    
        elif (c & 0xE0) == 0xC0:    
            c &= ~0xE0              
            c <<= 8                 
            c += ord(self._readStr(1))    
            c <<= 8                 
            c += ord(self._readStr(1))    
        elif (c & 0xF0) == 0xE0:    
            c &= ~0xF0              
            c <<= 8                 
            c += ord(self._readStr(1))    
            c <<= 8                 
            c += ord(self._readStr(1))    
            c <<= 8                 
            c += ord(self._readStr(1))    
        elif (c & 0xF8) == 0xF0:    
            c = ord(self._readStr(1))     
            c <<= 8                 
            c += ord(self._readStr(1))    
            c <<= 8                 
            c += ord(self._readStr(1))    
            c <<= 8                 
            c += ord(self._readStr(1))    
        return c                    

    def _writeStr(self, str):        
        n = 0;
        while n < len(str):
            r = self.connection.send(bytes(str[n:], 'UTF-8'))
            if r == 0: raise RuntimeError("connection closed by remote end")
            n += r                  

    def _writeByte(self, str):        
        n = 0;
        while n < len(str):
            r = self.connection.send(str[n:])
            if r == 0: raise RuntimeError("connection closed by remote end")
            n += r                  

    def _readStr(self, length):      
        ret = ''
        while len(ret) < length:
            s = self.connection.recv(length - len(ret))
            if s == '': raise RuntimeError("connection closed by remote end")
            ret += s.decode('UTF-8', 'replace')
        return ret
    
    @staticmethod
    def _prettyprint(array):
        ret = []
        for item in array:
            new_item={}
            for k, v in item.items():
                if k == ".id":
                    k = k[1:]
                    v = v[1:]
                new_item[k]=v
            ret.append(new_item)
        return ret
    
    @staticmethod
    def _unpretty(d):
        ret = {}
        for k, v in d.items():
            if k == "id":
                k = ".id"
            if k == "id" or k == ".id":
                if not v.startswith("*"):
                    v = "*"+v
            ret[k]=v
        return ret

    @staticmethod
    def _unpretty_id(ids):
        if type(ids) is int:
            ids = str(ids)
        if type(ids) is str:
            ids = ids.split(",")
        ret=[]
        for id in ids:
            if type(id) is int:
                id = str(id)
            if not id.startswith("*"):
                id = "*"+id
            ret.append(id)
        return ",".join(ret)
        

    def login(self, username, pwd):
        """
        Api login
        
        Return bool
        """
        if self.connection.fileno() < 0:
            return False
        for repl, attrs in self._talk(["/login", "=name=" + username,
                                      "=password=" + pwd]):
          if repl == '!trap':
            return False
          elif '=ret' in attrs.keys():
            chal = binascii.unhexlify(attrs['=ret'])
            md = hashlib.md5()
            md.update(b'\x00')
            md.update(pwd.encode())
            md.update(chal)
            for repl2, attrs2 in self._talk(["/login", "=name=" + username,
                   "=response=00" + binascii.hexlify(md.digest()).decode()]):
              if repl2 == '!trap':
                return False
        self._logged = True
        return True

    def close(self):
        """
        Close connection
        """
        self.connection.close()

    def send(self, words):
        """
        Send raw api command
        
        Return (bool, response)
        
        err,msg = send(["line1","line2",...])
        """
        if self.connection.fileno() < 0 or not self._logged:
            return False,[]
        rep = self._talk(words)
        if rep[0][0] == "!done":
            return True,[]
        if rep[0][0] == "!trap":
            return False,{ k.replace('=', ''): v for k, v in rep[0][1].items() }
        fullrep = []
        for line in rep:
            if line[0] == "!re":
                fullrep.append({ k[1:] if k.startswith('=') else k: v for k, v in line[1].items() })
        if self.debug:
            print("send result : ",fullrep)
        return True,fullrep
    
    @property
    def logged(self):
        """
        True if logged or False if not
        """
        return self._logged
    
    def find(self, path, search={}, itemlist="", operation="AND"):
        """
        find (mikrotik's print)
        
        path      : api path (eg: /ip/address)
        search    : 
                     "key" : "value"  -> key = value
                     "key" : "@"      -> key exist
                     "key" : "!"      -> key not exist
                     "key" : ">value" -> key greater than value
                     "key" : "<value" -> key less than value
        itemlist  : list of item to get (eg: "address" or "address,network"
        operation : AND, OR or NOT
        
        return (bool, [response])
        """
        command = [path + "/print"]
        search = self._unpretty(search)
        for k, v in search.items():
            if v.startswith("<"):
                opp = "<"
                v = v[1:]
            elif v.startswith(">"):
                opp = ">"
                v = v[1:]
            else:
                opp = "="
            if v == "@":
                command.append("?{}".format(k))
            elif v == "!":
                command.append("?-{}".format(k))
            else:
                command.append("?{}{}={}".format(opp,k,v))
        if operation == "AND":
            command.append("?#&")
        elif operation == "OR":
            command.append("?#|")
        elif operation == "NOT":
            command.append("?#!")
        if not ".id" in itemlist:
            itemlist = itemlist.replace("id",".id",1)
        if itemlist != "":
            command.append("=.proplist={}".format(itemlist))
        ret, resp = self.send(command)
        if ret:
            return ret, self._prettyprint(resp)
        else:
            return ret, resp
                           
    def add(self, path, params):
        """
        add (mikrotik's add)
        
        path      : api path (eg: /ip/address)
        params    : add parameters (eg: {'address': '192.168.0.1','interface':'ether4'})
        
        Return bool
        """
        command = [path + "/add"]
        params = self._unpretty(params)
        for k, v in params.items():
            command.append("={}={}".format(k,v))
        ret, resp = self.send(command)
        return ret

    def set(self, path, id, params):
        """
        set (mikrotik's set)
        
        path      : api path (eg: /ip/address)
        id        : mikrotik item(s) id(s) (eg : "1" or "*1" or "1,a" or "*1,a" or ["1","2"] or ["*1","2"]
        params    : set parameters (eg: {'address': '192.168.0.1','interface':'ether4'})
        
        Return bool
        """
        command = [path + "/set"]
        params = self._unpretty(params)
        command.append("=.id={}".format(self._unpretty_id(id)))
        for k, v in params.items():
            command.append("={}={}".format(k,v))
        ret, resp = self.send(command)
        return ret
        
    def remove(self, path, id):
        """
        remove (mikrotik's remove)
        
        path      : api path (eg: /ip/address)
        id        : mikrotik item(s) id(s) (eg : "1" or "*1" or "1,a" or "*1,a" or ["1","2"] or ["*1","2"]
                
        Return bool
        """
        command = [path + "/remove"]
        command.append("=.id={}".format(self._unpretty_id(id)))
        ret, resp = self.send(command)
        return ret
    
        
    def find_and_set(self, path, params, search={}, operation="AND"):
        """
        find_and_set (mikrotik's set [find...])
        
        path      : api path (eg: /ip/address)
        params    : set parameters (eg: {'address': '192.168.0.1','interface':'ether4'})
        search    : 
                     "key" : "value"  -> key = value
                     "key" : "@"      -> key exist
                     "key" : "!"      -> key not exist
                     "key" : ">value" -> key greater than value
                     "key" : "<value" -> key less than value
        operation : AND, OR or NOT
        
        Return bool
        """
        ret1, resp1 = self.find(path, search, "id", operation)
        if not ret1 or len(resp1) == 0:
            return False
        return self.set(path, [i["id"] for i in resp1], params)
    
    def find_and_remove(self, path, search={}, operation="AND"):
        """
        find_and_remove (mikrotik's remove [find...])
        
        path      : api path (eg: /ip/address)
        search    : 
                     "key" : "value"  -> key = value
                     "key" : "@"      -> key exist
                     "key" : "!"      -> key not exist
                     "key" : ">value" -> key greater than value
                     "key" : "<value" -> key less than value
        operation : AND, OR or NOT
        
        Return bool
        """
        ret1, resp1 = self.find(path, search, "id", operation)
        if not ret1 or len(resp1) == 0:
            return False
        return self.remove(path, [i["id"] for i in resp1])
    
