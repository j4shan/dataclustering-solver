"""Helvetica / Courier text metrics, so card geometry is measured, not typed."""

HELV = {
    ' ': 278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667, "'": 191,
    '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333, '.': 278, '/': 278,
    ':': 278, ';': 278, '<': 584, '=': 584, '>': 584, '?': 556, '@': 1015,
    '[': 278, '\\': 278, ']': 278, '^': 469, '_': 556, '`': 333,
    '{': 334, '|': 260, '}': 334, '~': 584, '·': 333, '×': 584, '…': 1000,
    'A': 667, 'B': 667, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722,
    'I': 278, 'J': 500, 'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778, 'P': 667,
    'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944, 'X': 667,
    'Y': 667, 'Z': 611,
    'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556, 'f': 278, 'g': 556, 'h': 556,
    'i': 222, 'j': 222, 'k': 500, 'l': 222, 'm': 833, 'n': 556, 'o': 556, 'p': 556,
    'q': 556, 'r': 333, 's': 500, 't': 278, 'u': 556, 'v': 500, 'w': 722, 'x': 500,
    'y': 500, 'z': 500,
}
for _d in '0123456789':
    HELV[_d] = 556

HELV_B = dict(HELV)
HELV_B.update({
    'A': 722, 'B': 722, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722,
    'I': 278, 'J': 556, 'K': 722, 'L': 611, 'M': 833, 'N': 722, 'O': 778, 'P': 667,
    'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944, 'X': 667,
    'Y': 667, 'Z': 611,
    'a': 556, 'b': 611, 'c': 556, 'd': 611, 'e': 556, 'f': 333, 'g': 611, 'h': 611,
    'i': 278, 'j': 278, 'k': 556, 'l': 278, 'm': 889, 'n': 611, 'o': 611, 'p': 611,
    'q': 611, 'r': 389, 's': 556, 't': 333, 'u': 611, 'v': 556, 'w': 778, 'x': 556,
    'y': 556, 'z': 500,
    ':': 333, ';': 333, '?': 611, '!': 333, "'": 238, '·': 350,
})

DEFAULT = 556


def adv(ch, bold):
    table = HELV_B if bold else HELV
    return table.get(ch, DEFAULT)


def text_w(s, size, bold=False, mono=False, tracking=0.0):
    """Width in px of one line."""
    if mono:
        return len(s) * size * 0.6 + tracking * max(len(s) - 1, 0)
    total = sum(adv(c, bold) for c in s) * size / 1000.0
    return total + tracking * max(len(s) - 1, 0)


def wrap(s, size, width, bold=False, mono=False):
    """Greedy word wrap at `width` px; honours explicit newlines."""
    out = []
    for para in s.split('\n'):
        if not para:
            out.append('')
            continue
        line = ''
        for word in para.split(' '):
            trial = word if not line else line + ' ' + word
            if text_w(trial, size, bold, mono) <= width or not line:
                line = trial
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def lines(s, size, width, bold=False, mono=False):
    return len(wrap(s, size, width, bold, mono))


def lh(size):
    """Line height drawio lays out at for a wrapped label."""
    return round(size * 1.42)
