# see: https://gkeepapi.readthedocs.io/en/latest/gkeepapi.html

import sys
import os
import configparser
import pickle
import gkeepapi
from pathlib import Path
import keyring

class KeepSession:
	def __init__ (self,unpickle=True):
		self.pickle = True
		home = str(Path.home())
		cfgpath = os.path.join(home,'google.ini')
		cfg = configparser.ConfigParser()
		try:
			cfg.read(cfgpath)
		except Exception as e:
			print("Failed to read google.ini",str(e))
			sys.exit(1)
		#print(cfg.sections())
		if 'keep' not in cfg.sections():
			print('Require [keep] section from google.ini')
			sys.exit(1)

		kc = cfg['keep']
		oops = False
		for p in ['cachedir','cachefile','keepID','keepAPW']:
			if p not in kc:
				print(f"google.ini keep section missing {p} parameter")
				oops = True
		if oops:
			sys.exit(2)

		self.kPath = os.path.join(kc['cachedir'],kc['cachefile'])
		loginDone = False
		if unpickle: # the client data retrieved is an authenticated session
			self.keep = pickle.load(open(self.kPath,'rb'))
			#self.keep.sync()  # If fails, authentication might be required?
			# !! add exception processing to detect login necessity !!
			loginDone = True
		else:
			self.keep = gkeepapi.Keep()
			kid = kc['keepID']
			print(f"Login with ID:",kid)
			try:
				mtok = keyring.get_password('Keep',kid)
				if mtok:
					print(f"Resuming with master token: {mtok}")
					try:
						success = self.keep.resume(kid,mtok)
						print("Keep resume success:",success)
						loginDone = True
					except Exception as e:
						print("Keep resume failed:",str(e))
				if not loginDone:
					print("Login with app password...")
					success = self.keep.login(kid,kc['keepAPW'])
					print("Keep login success:",success)
					loginDone = True
					mtok = self.keep.getMasterToken()
					try:
						keyring.set_password('Keep',kid,mtok) # alt to pickle
					except Exception as e:
						print("Failed to store password, probably cron-initiated"+str(e))
			except Exception as e:
				print('Keep login failed: '+str(e))
				sys.exit(3)
		self.keep.sync()

	def __enter__ (self):
		return(self)
	
	def __exit__ (self, exc_type, exc_value, traceback):
		#print('Discarding keep session')
		self.keep.sync()
		if (self.pickle):
			#print(f"Dump client in pickle format to {self.kPath}")
			pickle.dump(self.keep,open(self.kPath,'wb'))
		
	def getClient (self):
		return self.keep

	def nodeBrief (node):
		nbr = [ node.title ]
		ntp = node.type
		nbr.append("Node type: "+str(ntp))
		cs = str(node.color)
		nbr.append('color:'+cs)
		return ' / '.join(nbr)

	def nodeTally (node):
		return

