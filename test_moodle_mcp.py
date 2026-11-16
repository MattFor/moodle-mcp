import base64
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).with_name('moodle-mcp')
loader = SourceFileLoader('moodle_mcp', str(SCRIPT))
spec = spec_from_loader('moodle_mcp', loader)
assert spec
moodle = module_from_spec(spec)
loader.exec_module(moodle)

TOKEN = 'a' * 32


def sign_in_link(site, passport):
	site_id = hashlib.md5(f'{site}{passport}'.encode()).hexdigest()
	return 'moodlemobile://token=' + base64.b64encode(f'{site_id}:::{TOKEN}:::private'.encode()).decode()


class FakeMoodle(BaseHTTPRequestHandler):
	seen: list = []  # noqa: RUF012
	config: dict | None = {}  # noqa: RUF012

	def do_POST(self):
		raw = self.rfile.read(int(self.headers['Content-Length']))
		site = f'http://127.0.0.1:{self.server.server_port}'
		if self.path == '/lib/ajax/service-nologin.php':
			self.seen.append((self.path, json.loads(raw)))
			found = self.config is not None
			return self.reply(
				[{'error': False, 'data': {'wwwroot': site, **self.config}} if found else {'error': True}]
			)
		if self.path == '/webservice/upload.php':
			fields = {}
			for chunk in raw.split(b'--' + self.headers.get_param('boundary').encode())[1:-1]:
				head, _, body = chunk[2:].partition(b'\r\n\r\n')
				fields[re.search(rb' name="([^"]*)"', head)[1].decode()] = body[:-2]
				if filename := re.search(rb'filename="([^"]*)"', head):
					fields['filename'] = filename[1].decode()
			self.seen.append((self.path, fields))
			if fields['token'] != TOKEN.encode():
				return self.reply({'error': 'Invalid token', 'errorcode': 'invalidtoken'})
			itemid = int(fields['itemid']) or 555
			return self.reply([{'itemid': itemid, 'filename': fields['filename'], 'filearea': 'draft'}])
		fields = urllib.parse.parse_qsl(raw.decode())
		self.seen.append((self.path, fields))
		form = dict(fields)
		if self.path == '/login/token.php':
			good = (form['username'], form['password']) == ('student', 'secret')
			return self.reply({'token': TOKEN} if good else {'error': 'Invalid login, please try again'})
		if self.path == '/webservice/rest/server.php':
			function = form['wsfunction']
			if form['wstoken'] != TOKEN:
				body = {'exception': 'moodle_exception', 'errorcode': 'invalidtoken', 'message': 'Invalid token'}
			elif function == 'core_course_get_contents':
				body = [
					{
						'name': '<p>Lab <a href="https://x.test/a">one</a></p>',
						'intro': '<p>See<img alt="" src="https://x.test/p.png"/>below</p>',
						'summary': '',
						'timemodified': 1794000000,
					}
				]
			elif function == 'core_webservice_get_site_info':
				body = {'userid': 3, 'fullname': 'Test Student'}
			elif function == 'mod_assign_submit_for_grading':
				body = []
			else:
				body = {'exception': 'x', 'errorcode': 'accessexception', 'message': 'Access control exception'}
			return self.reply(body)
		if self.path == '/webservice/pluginfile.php/7/mod_resource/content/1/wyk%C5%82ad.pdf':
			return self.reply(b'%PDF-1.7 lecture', 'application/pdf')
		if self.path == '/webservice/pluginfile.php/8/mod_assign/introattachment/0/lab.ipynb':
			return self.reply({'cells': [], 'nbformat': 4})
		return self.reply({'error': 'File not found', 'errorcode': 'filenotfound'})

	def reply(self, body, content_type='application/json'):
		payload = body if isinstance(body, bytes) else json.dumps(body).encode()
		self.send_response(200)
		self.send_header('Content-Type', content_type)
		self.send_header('Content-Length', str(len(payload)))
		self.end_headers()
		self.wfile.write(payload)

	def log_message(self, format, *args):
		pass


class Base(unittest.TestCase):
	def setUp(self):
		self.dir = tempfile.TemporaryDirectory()
		self.addCleanup(self.dir.cleanup)
		self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), FakeMoodle)
		threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
		self.addCleanup(self.httpd.server_close)
		self.addCleanup(self.httpd.shutdown)
		FakeMoodle.seen.clear()
		FakeMoodle.config = {}
		self.site = f'http://127.0.0.1:{self.httpd.server_port}'
		moodle.CONFIG = Path(self.dir.name) / 'config' / 'login.json'
		moodle.CACHE = Path(self.dir.name) / 'cache'
		moodle.save(self.site, TOKEN)


class Pure(Base):
	def test_check(self):
		for name in ('core_course_get_contents', 'core_course_search_courses', 'mod_assign_get_assignments'):
			moodle.check(name, write=False)
		for name in (
			'mod_assign_save_submission',
			'mod_assign_submit_for_grading',
			'core_message_send_instant_messages',
		):
			with self.assertRaisesRegex(ValueError, 'use moodle_write', msg=name):
				moodle.check(name, write=False)
			moodle.check(name, write=True)
		for name in (
			'tool_mobile_get_autologin_key',
			'tool_mobile_get_tokens_for_qr_login',
			'core_auth_request_password_reset',
			'tool_mobile_call_external_functions',
		):
			for write in (False, True):
				with self.assertRaisesRegex(ValueError, 'blocked', msg=name):
					moodle.check(name, write)
		for name in ('core_course_get_contents&wstoken=x', 'Core_get_x', '', None):
			with self.assertRaisesRegex(ValueError, 'Not a web-service function', msg=repr(name)):
				moodle.check(name, write=True)

	def test_flatten(self):
		self.assertEqual(
			list(moodle.flatten({'courseids': [3, 5], 'options': [{'name': 'a', 'value': True}], 'skip': None})),
			[('courseids[0]', '3'), ('courseids[1]', '5'), ('options[0][name]', 'a'), ('options[0][value]', '1')],
		)

	def test_saved_login(self):
		self.assertEqual(moodle.signed_in(), (self.site, TOKEN))
		self.assertEqual(moodle.CONFIG.stat().st_mode & 0o777, 0o600)
		self.assertEqual([p.name for p in moodle.CONFIG.parent.iterdir()], ['login.json'])
		for text in ('', '{}', '[]', '{"site": "x"}'):
			moodle.CONFIG.write_text(text)
			with self.assertRaisesRegex(ValueError, 'Not signed in', msg=text):
				moodle.signed_in()
		moodle.CONFIG.unlink()
		with self.assertRaisesRegex(ValueError, 'Not signed in'):
			moodle.signed_in()

	def test_key_from_link(self):
		link = sign_in_link(self.site, 'p4ss')
		self.assertEqual(moodle.key_from_link(f' {link}\n', self.site, 'p4ss'), TOKEN)
		payload = link.partition('token=')[2]
		quoted = f'"moodlemobile://token={urllib.parse.quote(payload, safe="")}"'
		self.assertEqual(moodle.key_from_link(quoted, self.site, 'p4ss'), TOKEN)
		with self.assertRaisesRegex(ValueError, 'another sign-in'):
			moodle.key_from_link(link, self.site, 'other')
		for junk in ('', 'moodlemobile://token=', 'https://moodle.test/my/', 'moodlemobile://token=!!!'):
			with self.assertRaisesRegex(ValueError, 'not the sign-in link', msg=junk):
				moodle.key_from_link(junk, self.site, 'p4ss')

	def test_login_takes_link_from_browser_or_terminal(self):
		link = 'moodlemobile://token=abc'
		with self.assertRaisesRegex(ValueError, 'waiting'):
			moodle.hand_over(link)
		self.assertEqual(self.receive('', from_browser=link), link)
		self.assertEqual(self.receive(f'\n \n{link}\n'), f'{link}\n')
		self.assertFalse((moodle.CACHE / '.login').exists())

	def receive(self, typed, from_browser=None):
		read_end, write_end = os.pipe()
		os.write(write_end, typed.encode())
		os.close(write_end)
		with os.fdopen(read_end) as stdin, mock.patch.object(sys, 'stdin', stdin):
			if not from_browser:
				return moodle.receive_link()
			received = []
			reader = threading.Thread(target=lambda: received.append(moodle.receive_link()))
			reader.start()
			for _ in range(500):
				try:
					moodle.hand_over(from_browser)
					break
				except ValueError:
					time.sleep(0.01)  # login has not opened the pipe yet
			reader.join(5)
			return received[0]


class Calls(Base):
	def test_read(self):
		result = moodle.tidy(moodle.call('core_course_get_contents', {'courseid': 7}))
		self.assertEqual(result[0]['name'], 'Lab one (https://x.test/a)')
		self.assertEqual(result[0]['intro'], 'See (image https://x.test/p.png) below')
		self.assertNotIn('summary', result[0])
		self.assertRegex(result[0]['timemodified_local'], r'^2026-11-\d\dT\d\d:\d\d[+-]\d\d:\d\d$')
		path, fields = FakeMoodle.seen[0]
		self.assertEqual(path, '/webservice/rest/server.php')
		self.assertIn(('courseid', '7'), fields)
		self.assertIn(('moodlewsrestformat', 'json'), fields)

	def test_write(self):
		args = {'assignmentid': 4, 'acceptsubmissionstatement': True}
		self.assertEqual(moodle.call('mod_assign_submit_for_grading', args, write=True), [])
		fields = FakeMoodle.seen[0][1]
		self.assertIn(('assignmentid', '4'), fields)
		self.assertIn(('acceptsubmissionstatement', '1'), fields)

	def test_args_cannot_replace_the_function(self):
		args = {'wsfunction': 'mod_assign_submit_for_grading', 'moodlewsrestformat': 'xml'}
		self.assertEqual(moodle.call('core_webservice_get_site_info', args)['userid'], 3)
		self.assertEqual(FakeMoodle.seen[0][1][-1], ('moodlewsrestformat', 'json'))

	def test_errors(self):
		with self.assertRaisesRegex(ValueError, 'accessexception: Access control exception'):
			moodle.call('core_user_get_users', {})
		with self.assertRaisesRegex(ValueError, 'use moodle_write'):
			moodle.call('mod_quiz_start_attempt', {'quizid': 1})
		moodle.save(self.site, 'b' * 32)
		with self.assertRaisesRegex(ValueError, f'invalidtoken.*moodle-mcp login {self.site}'):
			moodle.call('core_course_get_contents', {})
		self.assertEqual(len(FakeMoodle.seen), 2)

	def test_upload(self):
		homework = Path(self.dir.name) / 'zadanie 1 ł.pdf'
		homework.write_bytes(b'%PDF homework\r\n--not-a-boundary')
		self.assertEqual(moodle.upload(str(homework))[0]['itemid'], 555)
		fields = FakeMoodle.seen[0][1]
		self.assertEqual(fields['filename'], 'zadanie 1 ł.pdf')
		self.assertEqual(
			(fields['file'], fields['filearea'], fields['itemid']), (homework.read_bytes(), b'draft', b'0')
		)
		self.assertEqual(moodle.upload(str(homework), 555)[0]['itemid'], 555)
		moodle.save(self.site, 'b' * 32)
		with self.assertRaisesRegex(ValueError, 'invalidtoken: Invalid token'):
			moodle.upload(str(homework))
		with self.assertRaises(FileNotFoundError):
			moodle.upload(str(homework.with_name('missing.pdf')))

	def test_download(self):
		url = f'{self.site}/pluginfile.php/7/mod_resource/content/1/wyk%C5%82ad.pdf?forcedownload=1'
		target = moodle.download(url)
		self.assertEqual((target.parent.parent, target.name), (moodle.CACHE, 'wykład.pdf'))
		self.assertEqual(target.read_bytes(), b'%PDF-1.7 lecture')
		self.assertEqual(FakeMoodle.seen[0][1], [('token', TOKEN)])
		self.assertEqual(moodle.download(url), target)
		mine = Path(self.dir.name) / 'mine'
		self.assertEqual(moodle.download(url, str(mine)), mine / 'wykład.pdf')
		with self.assertRaisesRegex(ValueError, 'already exists'):
			moodle.download(url, str(mine))
		with self.assertRaisesRegex(ValueError, 'refused the file'):
			moodle.download(f'{self.site}/pluginfile.php/9/gone.pdf')
		self.assertEqual([p.name for p in moodle.CACHE.glob('*/*')], ['wykład.pdf'])
		notebook = moodle.download(f'{self.site}/pluginfile.php/8/mod_assign/introattachment/0/lab.ipynb', str(mine))
		self.assertEqual(json.loads(notebook.read_text()), {'cells': [], 'nbformat': 4})

	def test_token_never_leaves_the_site(self):
		before = len(FakeMoodle.seen)
		for url in (
			'https://evil.test/pluginfile.php/1/a.pdf',
			f'{self.site}.evil.test/pluginfile.php/1/a.pdf',
			f'{self.site}@evil.test/pluginfile.php/1/a.pdf',
			f'{self.site}/login/index.php',
			'file:///etc/passwd',
		):
			with self.assertRaisesRegex(ValueError, 'Only', msg=url):
				moodle.download(url)
		self.assertEqual(len(FakeMoodle.seen), before)


class Login(Base):
	def setUp(self):
		super().setUp()
		moodle.CONFIG.unlink()
		quiet = contextlib.redirect_stdout(io.StringIO())
		quiet.__enter__()
		self.addCleanup(quiet.__exit__, None, None, None)

	def test_password(self):
		FakeMoodle.config = {'typeoflogin': 1}
		with mock.patch('builtins.input', return_value='student'), mock.patch('getpass.getpass', return_value='secret'):
			moodle.login(f'{self.site}/')
		self.assertEqual(moodle.signed_in(), (self.site, TOKEN))
		with (
			mock.patch('builtins.input', return_value='student'),
			mock.patch('getpass.getpass', return_value='wrong'),
			self.assertRaisesRegex(ValueError, 'Invalid login'),
		):
			moodle.login(self.site)

	def test_browser(self):
		FakeMoodle.config = {'typeoflogin': 1, 'identityproviders': [{'name': 'Microsoft'}]}
		read_end, write_end = os.pipe()
		os.write(write_end, f'{sign_in_link(self.site, "p4ss")}\n'.encode())
		os.close(write_end)
		with (
			os.fdopen(read_end) as stdin,
			mock.patch.object(sys, 'stdin', stdin),
			mock.patch.dict(os.environ, {'DISPLAY': ':0'}),
			mock.patch('secrets.token_hex', return_value='p4ss'),
			mock.patch('webbrowser.open') as browser,
		):
			moodle.login(self.site)
		self.assertEqual(moodle.signed_in(), (self.site, TOKEN))
		self.assertRegex(browser.call_args[0][0], rf'^{self.site}/admin/tool/mobile/launch\.php\?.*passport=p4ss')

	def test_not_a_moodle_site(self):
		with self.assertRaisesRegex(ValueError, 'does not look like a Moodle site'):
			moodle.login(f'{self.site}/nothing')
		FakeMoodle.config = None
		with self.assertRaisesRegex(ValueError, 'does not allow the Moodle app'):
			moodle.login(self.site)
		self.assertFalse(moodle.CONFIG.exists())


class Protocol(unittest.TestCase):
	def test_stdio(self):
		lines = [
			{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26'}},
			{'jsonrpc': '2.0', 'method': 'notifications/initialized'},
			{'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
			{
				'jsonrpc': '2.0',
				'id': 3,
				'method': 'tools/call',
				'params': {'name': 'moodle_read', 'arguments': {'function': 'mod_quiz_start_attempt'}},
			},
			{'jsonrpc': '2.0', 'id': 4, 'method': 'resources/list'},
			{'jsonrpc': '2.0', 'id': 5, 'method': 'ping'},
		]
		text = '\n'.join(json.dumps(line) for line in lines) + '\n\nnot json\n'
		with tempfile.TemporaryDirectory() as home:
			env = {**os.environ, 'XDG_CONFIG_HOME': home, 'XDG_CACHE_HOME': home}
			run = subprocess.run(
				[sys.executable, str(SCRIPT)],
				input=text,
				capture_output=True,
				text=True,
				timeout=30,
				check=True,
				env=env,
			)
		replies = [json.loads(line) for line in run.stdout.splitlines()]
		self.assertEqual([r['id'] for r in replies], [1, 2, 3, 4, 5])
		self.assertEqual(replies[0]['result']['protocolVersion'], '2025-03-26')
		names = [t['name'] for t in replies[1]['result']['tools']]
		self.assertEqual(names, ['moodle_read', 'moodle_write', 'moodle_upload', 'moodle_download'])
		self.assertTrue(replies[2]['result']['isError'])
		self.assertIn('use moodle_write', replies[2]['result']['content'][0]['text'])
		self.assertEqual(replies[3]['error']['code'], -32601)
		self.assertEqual(replies[4]['result'], {})
		self.assertEqual(run.stderr, '')
		usage = subprocess.run(
			[sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True, timeout=30, check=False
		)
		self.assertEqual((usage.returncode, usage.stdout), (1, ''))
		self.assertIn('moodle-mcp login <site>', usage.stderr)


if __name__ == '__main__':
	unittest.main()
