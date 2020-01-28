from __future__ import print_function
import pickle
import os.path
import sys
import re
import time
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']

validPersonFields = [
		'addresses', 
		'ageRanges', 
		'biographies', 
		'birthdays', 
		'braggingRights', 
		'coverPhotos', 
		'emailAddresses', 
		'events', 
		'genders', 
		'imClients', 
		'interests', 
		'locales', 
		'memberships', 
		'metadata', 
		'names', 
		'nicknames', 
		'occupations', 
		'organizations', 
		'phoneNumbers', 
		'photos', 
		'relations', 
		'relationshipInterests', 
		'relationshipStatuses', 
		'residences', 
		'sipAddresses', 
		'skills', 
		'taglines', 
		'urls', 
		'userDefined',
]
def getCreds ():
	import os
	crdir = os.environ['GOOGLE_CREDDIR']
	tokpath = os.path.join(crdir,'token.pickle')
	credpath = os.path.join(crdir,'credentials.json')
	creds = None
	# The file token.pickle stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists(tokpath):
		with open(tokpath, 'rb') as token:
			creds = pickle.load(token)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				credpath, SCOPES)
			creds = flow.run_local_server()
		# Save the credentials for the next run
		with open(tokpath, 'wb') as token:
			pickle.dump(creds, token)
	return creds

def dumpItem (i,depth,npath):
	it = type(i).__name__
	if it == 'dict':
		for kinfo, info in i.items():
			npath.append(kinfo)
			dumpItem(info,depth+1,npath)
	elif it == 'list':
		for j in range(0,len(i)):
			sj = str(j)
			npath.append(sj)
			dumpItem(i[j],depth+1,npath)
	else:
		print("%-50s" % (it+": "+str(i)),
			  "  ["+'.'.join(npath)+']')
	npath.pop()

def getService (creds):
	return build('people', 'v1', credentials=creds)

# Call the Groups API
def getGroups (service,limit=100):
	results = service.contactGroups().list(
		pageSize=limit
	).execute()
	groups = results.get('contactGroups',[])
	return groups

# Call the People API
def getPeople (service,limit=2000):
	results = service.people().connections().list(
		resourceName='people/me',
		pageSize=limit, # max 2000 in 4/2019
		#personFields='names,emailAddresses'
		personFields=','.join(validPersonFields),
	).execute()
	connections = results.get('connections',[])
	return(connections)

class Walker ():
	def __init__ (self,session):
		self.session = session
		self.nodesProcessed = {}
		self.desc = []
		self.clumps = {}

	def relateDescendant (self,d,ulkey):
		cql = ('match (me:GPunique {ulkey:{ulkey}}) '
			   'match (d:GPunique {ulkey:{d}}) '
			   'create (d)-[re:BELONGS_TO]->(me)')
		print('  RELATE:',cql,f'with {d}->{ulkey}')
		try:
			self.session.run(cql,d=d,ulkey=ulkey)
		except Exception as e:
			print('Failed to relate descendant:',str(e))
			sys.exit(3)
		
	def writeNode (self,nlabel,ulkey,p):
		p['ulkey'] = ulkey # temp key for later relationship addition
		cql = ( f'merge (n:{nlabel}:GPunique '+ '{' +
				', '.join([k+':{'+k+'}' for k in p.keys()]) +
				' })'
				)
		print('NOTE:',cql,'with','  '.join([f'"{d}"' for d in p.values()]))
		try:
			self.session.run(cql,**p)
			self.session.sync()
		except Exception as e:
			print('writeNode CQL failed wtih:',str(e))
			sys.exit(2)
		if nlabel not in self.nodesProcessed:
			self.nodesProcessed[nlabel] = 0
		self.nodesProcessed[nlabel] += 1
		return ulkey
		
	def noteWalk (self,loc,locpath,label,propstack,me={},parent={'ukey':''}):
		print('noteWalk at',locpath)
		ukey = '.'.join(locpath)
		me['ukey'] = ukey
		if 'branches' not in parent:
			parent['branches'] = []
		parent['branches'] += [me]
		loctype = type(loc).__name__
		nlabel = 'GP'+label
		desc = []
		if loctype == 'dict':
			me['remark'] = 'DICT'
			me['branches'] = []
			for k,v in loc.items():
				#skey = ukey+'.'+k
				myprops = self.noteWalk(v,locpath+[k],k,propstack+[{}],
										me={},parent=me)
				#print(f'  Props accum for {nlabel} {".".join(locpath)}:',myprops)
			myprops['basename'] = label
			self.writeNode(nlabel,".".join(locpath),myprops)
		elif loctype == 'list':
			me['remark'] = 'LIST'
			me['branches'] = []
			for i in range(0,len(loc)):
				v = loc[i]
				#skey = ukey+'.'+str(i)
				myprops = self.noteWalk(v,locpath+[str(i)],label,propstack+[{}],
										me={},parent=me)
				#print(f'  Props accum for {nlabel} {".".join(locpath)}:',myprops)
			myprops['basename'] = label
			self.writeNode(nlabel,".".join(locpath),myprops)
		else:   # add a property to parent node
			if re.match('^\d+$',locpath[-1]):
				me['remark'] = 'ELEMENT'
				skey = ".".join(locpath+[str(loc)])
				me['branches'] = [{ 'ukey':skey }] # no subkeys
				#print("A NUMERIC ending") # write as node, but fudge unique key
				propstack[-1]['value'] = loc
				propstack[-1]['basename'] = label
				self.writeNode(nlabel,skey,propstack[-1])
			else: # usual case
				me['remark'] = 'PROPERTY'
				#print("  ADD PROP:",loc)
				propstack[-2][locpath[-1]] = loc
		return propstack[-2]

	def relateWalk (self,me,pkey=''):
		print('relateWalk at',me['ukey'],'child of',pkey)
		if pkey != '':
			self.relateDescendant(me['ukey'],pkey)
		if 'branches' in me:
			tree = me['branches']
			for b in me['branches']:
				self.relateWalk(b,pkey=me['ukey'])
