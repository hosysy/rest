# -*- coding: utf8 -*-
"""
 Copyright (C) 2008-2014 NURIGO
 http://www.coolsms.co.kr
"""

__version__ = "1.0beta"

from hashlib import md5
import httplib,urllib,sys,hmac,mimetypes,base64,array,uuid,json,time

def post_multipart(host, selector, fields, files):
	content_type, body = encode_multipart_formdata(fields, files)
	h = httplib.HTTPS(host)
	h.putrequest('POST', selector)
	h.putheader('content-type', content_type)
	h.putheader('content-length', str(len(body)))
	h.endheaders()
	h.send(body)
	errcode, errmsg, headers = h.getreply()
	return errcode, errmsg, h.file.read()

def encode_multipart_formdata(fields, files):
	BOUNDARY = str(uuid.uuid1())
	CRLF = '\r\n'
	L = []
	for key, value in fields.items():
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"' % key)
		L.append('')
		L.append(value)
	L.append('')
	body = CRLF.join(L)
	for key, value in files.items():
		#L.append('--' + BOUNDARY)
		#L.append('Content-Type: %s' % get_content_type(value['filename']))
		#L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, value['filename']))
		#L.append('')
		#L.append(value['content'])
		body = body + '--' + BOUNDARY + CRLF
		body = body + 'Content-Type: %s' % get_content_type(value['filename']) + CRLF
		body = body + 'Content-Disposition: form-data; name="%s"; filename="%s"' % (key, value['filename']) + CRLF
		body = body + CRLF
		body = body.encode('utf-8') + value['content'] + CRLF
	#L.append('--' + BOUNDARY + '--')
	#L.append('')
	body = body + '--' + BOUNDARY + '--' + CRLF
	body = body + CRLF
	content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
	return content_type, body

def get_content_type(filename):
	return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


class rest:
	host = 'api.coolsms.co.kr'
	port = 443
	version = '1'
	api_key = None
	api_secret = None
	srk = None
	uesr_id = None
	mtype = 'sms'
	imgfile = None
	error_string = None
	test = False

	def __init__(self, api_key, api_secret, srk = None, test = False, version = None):
		self.api_key = api_key
		self.api_secret = api_secret
		self.srk = srk
		self.test = test
		if version:
			self.version = version

	def __get_signature__(self):
		salt = str(uuid.uuid1())
		timestamp = str(int(time.time()))
		data = timestamp + salt
		return timestamp, salt, hmac.new(self.api_secret, data, md5)

	def __set_error__(self, error_str):
		self.error_string = error_str

	def get_type(self):
		return self.mtype

	def get_error(self):
		return self.error_string

	def set_type(self, mtype):
		if mtype.lower() not in ['sms','lms','mms']:
			return False
		self.mtype = mtype.lower()
		return True

	def set_image(self, image):
		self.imgfile = image

	def send(self, to=None, text=None, sender=None, mtype=None, subject=None, image=None, datetime=None, extension=None):
		if type(to) == list:
			to = ','.join(to)

		if mtype:
			if mtype.lower() not in ['sms','lms','mms']:
				self.__set_error__('invalid message type')
				return False
		else:
			mtype = self.get_type()

		timestamp, salt, signature = self.__get_signature__()

		host = self.host + ':' + str(self.port)
		selector = "/%s/send" % self.version
		fields = {'api_key':self.api_key, 'timestamp':timestamp, 'salt':salt, 'signature':signature.hexdigest(), 'type':mtype}
		if self.test:
			fields['mode'] = 'test'
		if self.srk != None:
			fields['srk'] = self.srk
		if to:
			fields['to'] = to
		if text:
			fields['text'] = text
		if sender:
			fields['from'] = sender
		if subject:
			fields['subject'] = subject
		if datetime:
			fields['datetime'] = datetime
		if extension:
			fields['extension'] = extension

		if image == None:
			image = self.imgfile

		if mtype.lower() == 'mms':
			if image == None:
				self.__set_error__('image file path input required')
				return False
			try:
				with open(image, 'rb') as content_file:
					content = content_file.read()
			except IOError as e:
				self.__set_error__("I/O error({0}): {1}".format(e.errno, e.strerror))
				return False
			except:
				self.__set_error__("Unknown error")
				return False
			files = {'image':{'filename':image,'content':content}}
		else:
			files = {}

		status, reason, response = post_multipart(host, selector, fields, files)
		print response
		if status != 200:
			try:
				err = json.loads(response)
			except:
				self.__set_error__("%u:%s" % (status, reason))
				return False
			self.__set_error__("%s:%s" % (err['code'], reason))
			return False
		return json.loads(response)

	def status(self, page = 1, count = 20, s_rcpt = None, s_start = None, s_end = None, mid = None):
		params = dict()
		if page:
			params['page'] = page
		if count:
			params['count'] = count
		if s_rcpt:
			params['s_rcpt'] = s_rcpt
		if s_start:
			params['s_start'] = s_start
		if s_end:
			params['s_end'] = s_end
		if mid:
			params['mid'] = mid
		response, obj = self.request_get('sent', params)
		return obj

	def balance(self):
		timestamp, salt, signature = self.__get_signature__()
		response, obj = self.request_get('balance')
		return int(obj['cash']), int(obj['point'])

	def cancel(self, mid = None, gid = None):
		if mid == None and gid == None:
			return False

		params = dict()
		if mid:
			params['mid'] = mid
		if gid:
			params['gid'] = gid

		response, obj = self.request_post('cancel', params)
		if response.status == 200:
			return True
		return False

	def request_get(self, resource, params = None):
		timestamp, salt, signature = self.__get_signature__()
		base_params = {'api_key':self.api_key, 'timestamp':timestamp, 'salt':salt, 'signature':signature.hexdigest()}
		if params:
			base_params = dict(base_params.items() + params.items())
		params_str = urllib.urlencode(base_params)
		headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
		conn = httplib.HTTPSConnection(self.host, self.port)
		conn.request("GET", "/%s/%s?" % (self.version, resource) + params_str, None, headers)
		response = conn.getresponse()
		data = response.read()
		conn.close()
		obj = response, json.loads(data)
		return obj

	def request_post(self, resource, params = None):
		timestamp, salt, signature = self.__get_signature__()
		base_params = {'api_key':self.api_key, 'timestamp':timestamp, 'salt':salt, 'signature':signature.hexdigest()}
		if params:
			base_params = dict(base_params.items() + params.items())
		params_str = urllib.urlencode(base_params)
		headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
		conn = httplib.HTTPSConnection(self.host, self.port)
		conn.request("GET", "/%s/%s?" % (self.version, resource) + params_str, None, headers)
		response = conn.getresponse()
		data = response.read()
		conn.close()
		json_obj = json.loads(data)
		return response, json_obj
