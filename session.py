import sublime, sublime_plugin
import threading
from . import swank
from functools import partial
import socket

SESSIONS = {}
SESSIONS_LOCK = threading.RLock()

def for_window(window):
    SESSIONS_LOCK.acquire()
    session = SESSIONS.get(window.id())
    SESSIONS_LOCK.release()
    return session

def set_session(window, session):
    SESSIONS_LOCK.acquire()
    SESSIONS[window.id()] = session
    SESSIONS_LOCK.release()


class EnsimeSession:
    def __init__(self, port):
        self.client = EnsimeClient(port)


class EnsimeClient:
    def __init__(self, port):
        self.msg_id = 0
        self._id_lock = threading.RLock()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(('localhost', port))
        self._callbacks_lock = threading.RLock()
        self._msg_callbacks = {}

        self.listener = EnsimeListener(self.socket, self)
        sublime.set_timeout_async(partial(self.listener.listen_loop), 0)

    def _next_msg_id(self):
        self._id_lock.acquire()
        try:
            self.msg_id += 1
            return self.msg_id
        finally:
            self._id_lock.release()

    def handle_ensime_msg(self, msg):
        if not swank.is_ok(msg):
            # TODO: Error handling
            print("NOT OK")

        msg_id = msg[-1]
        sublime.set_timeout(print('MSG_ID: ' + str(msg_id)), 0)
        self._callbacks_lock.acquire()
        callback = self._msg_callbacks.get(msg_id, lambda *args: None)
        if msg_id in self._msg_callbacks:
            self._msg_callbacks.pop(msg_id)
        self._callbacks_lock.release()

        # Callback with body of the message
        callback(msg[1][1])

    def _set_callback(self, msg_id, callback):
        self._callbacks_lock.acquire()
        self._msg_callbacks[msg_id] = callback
        self._callbacks_lock.release()

    def patch_source(self, file_name, edits):
        msg_id = self._next_msg_id()

        def format_edit(edit):
            diff = edit[2].replace('"', '\\"').lstrip()
            return '("{0}" {1} "{2}")'.format(edit[0], edit[1], diff)

        edits_formatted = map(format_edit, edits)
        edits_msg = '(' + ' '.join(edits_formatted) + ')'
        msg = '(:swank-rpc (swank:patch-source "{0}" {1}) {2})'.format(file_name, edits_msg, msg_id)
        real_msg = "%06x" % len(msg) + msg
        print(msg)
        print(real_msg)

        self.socket.sendall(real_msg.encode('utf-8'))


    def inspect_type_at_point(self, file_name, pt):
        msg_id = self._next_msg_id()
        msg = '(:swank-rpc (swank:inspect-type-at-point "{0}" {1}) {2})'.format(file_name, pt, msg_id)
        real_msg = "%06x" % len(msg) + msg

        def callback(msg):
            sublime.message_dialog(str(msg))

        self._set_callback(msg_id, callback)
        self.socket.sendall(real_msg.encode('utf-8'))

    def type_at_point(self, file_name, pt):
        msg_id = self._next_msg_id()
        msg = '(:swank-rpc (swank:type-at-point "{0}" {1}) {2})'.format(file_name, pt, msg_id)
        real_msg = "%06x" % len(msg) + msg

        def callback(msg):
            print(msg)
            sublime.message_dialog(str(msg))

        self._set_callback(msg_id, callback)
        self.socket.sendall(real_msg.encode('utf-8'))

    def symbol_at_point(self, file_name, pt):
        msg_id = self._next_msg_id()
        msg = '(:swank-rpc (swank:symbol-at-point "{0}" {1}) {2})'.format(file_name, pt, msg_id)
        real_msg = "%06x" % len(msg) + msg

        def callback(msg):
            # Gonna get the full type here:
            def parse_type_info(sexp_type):
                if not sexp_type:
                    return ''

                type_info = ''
                opening, closing = '[', ']'
                result_type, type_args = sexp_type.get('result-type'), sexp_type.get('type-args')
                if result_type:
                    type_info = parse_type_info(result_type)
                else:
                    name = sexp_type['name']
                    if name.startswith('Tuple'):
                        opening, closing = '(', ')'
                    elif name == '<repeated>':
                        opening, closing = '', '*'
                    else:
                        type_info += name

                    if type_args:
                        type_info += opening + parse_type_args(type_args) + closing

                return type_info

            def parse_type_args(sexp_type_args):
                type_args = []
                for type_arg in sexp_type_args:
                    type_args.append(parse_type_info(type_arg))

                return ', '.join(type_args)


            info = parse_type_info(swank.extract(msg).get('type'))
            sublime.set_timeout(partial(sublime.message_dialog, info), 0)

        self._set_callback(msg_id, callback)
        self.socket.sendall(real_msg.encode('utf-8'))

    def typecheck_file(self, file_name):
        msg_id = self._next_msg_id()
        msg = '(:swank-rpc (swank:typecheck-file (:file "{0}")) {1})'.format(file_name, msg_id)
        real_msg = "%06x" % len(msg) + msg

        def callback(msg):
            print(msg)

        self._set_callback(msg_id, callback)
        self.socket.sendall(real_msg.encode('utf-8'))

    def typecheck_all(self):
        msg_id = self._next_msg_id()
        msg = '(:swank-rpc (swank:typecheck-all) {0})'.format(msg_id)
        real_msg = "%06x" % len(msg) + msg

        def callback(msg):
            print(msg)
            sublime.message_dialog(str(msg))

        self._set_callback(msg_id, callback)
        self.socket.sendall(real_msg.encode('utf-8'))


class EnsimeListener:
    def __init__(self, socket, client):
        self.socket = socket
        self.listening = True
        self.client = client

    def end(self):
        self.listening = False

    def listen_loop(self):
        state = 0
        data = b''
        wanted_length = 0
        while self.listening:
            try:
                data += self.socket.recv(32)
                if state == 0 and len(data) >= 6:
                    state = 1
                    wanted_length = int(data[:6], 16)
                    data = data[6:]
                elif state == 1 and len(data) >= wanted_length:
                    state = 0
                    msg = swank.parse(data[:wanted_length].decode('utf-8'))
                    self.client.handle_ensime_msg(msg)
                    data = data[wanted_length:]
            except Exception as e:
                print(e)
