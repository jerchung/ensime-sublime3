import re

KEY_REGEX  = r"""(?s)^:(?P<key>[a-zA-Z:\-]+)(?P<rest>.*)"""
WORD_REGEX = r"""(?s)^(?P<word>[a-zA-Z:\-]+)(?P<rest>.*)"""
WS_REGEX   = r"""(?s)^\s+(?P<rest>.*)"""
INT_REGEX  = r"""(?s)^(?P<int>[0-9]+)(?P<rest>.*)"""
STR_REGEX  = r"""(?s)^"(?P<string>.*?)"(?P<rest>.*)"""

class Keyword:
  def __init__(self, s):
    self.val = s
  def __repr__(self):
    return self.val
  def __eq__(self, k):
    return type(k) == type(self) and self.val == k.val

def is_ok(msg):
    return msg and msg[0] == Keyword('return') and msg[1] == Keyword('ok')

def msg_id(msg):
    return msg[-1]

def parse(sexp):
    result, remaining = parse_sexp(sexp)
    if remaining.strip():
        raise SyntaxError('Swank expression could not be completely parsed')
    return result

def parse_sexp(sexp):
    token, remaining = next_sexp_token(sexp)
    if token == '(':
        return parse_swank_list(remaining)
    else:
        return token, remaining

def parse_swank_list(sexp):
    contents = []
    while True:
        token, remaining = next_sexp_token(sexp)
        if token is None:
            raise SyntaxError("Closing ) expected but end of string reached.")
        elif token == ')':
            return contents, remaining
        else:
            token, remaining = parse_sexp(sexp)
            sexp = remaining
            contents.append(token)

def next_sexp_token(sexp):
    if not sexp:
        return None, ''

    # Skip whitepsaces
    while True:
        ws = re.match(WS_REGEX, sexp)
        if ws is None:
            break
        sexp = ws.group('rest')
        if not sexp:
            return None, ''

    # Check for parens
    char = sexp[0]
    if char == '(' or char == ')':
        return char, sexp[1:]
    # Match other regexes
    key = re.match(KEY_REGEX, sexp)
    if key is not None:
        return Keyword(key.group('key')), key.group('rest')

    word = re.match(WORD_REGEX, sexp)
    if word is not None:
        w = word.group('word')
        w = {'t': True, 'nil': False}.get(w, w)
        return w, word.group('rest')

    num = re.match(INT_REGEX, sexp)
    if num is not None:
        return int(num.group('int')), num.group('rest')

    strng = re.match(STR_REGEX, sexp)
    if strng is not None:
        return strng.group('string'), strng.group('rest')

    raise SyntaxError('Could not match {0} to a type before end of expression'.format(sexp))

# Use for sexp expressions that have been validated that will definitely be in
# a mappable form.  Do things recursively
def extract(sexp):
    check = sexp[0]
    if isinstance(check, list):
        result = map(lambda s: extract(s), sexp)
    elif isinstance(check, Keyword):
        result = {}
        for i in range(0, len(sexp), 2):
            key, val = sexp[i].val, sexp[i + 1]
            if isinstance(val, list):
                val = extract(val)
            result[key] = val
    else:
        raise RuntimeError('Invalid sexpression provided to extract function')

    return result
