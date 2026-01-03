"""
Lexer for Rosh - converts source code into tokens
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
from .errors import RoshSyntaxError


class TokenType(Enum):
    # Literals
    NUMBER = auto()
    NUMBER_PX = auto()      # Pixel value: 400px (explicit pixels, not percentage)
    NUMBER_PERCENT = auto() # Percentage: 50% (explicit percentage)
    STRING = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()

    # Keywords
    CREATE = auto()
    OBJECT = auto()
    NUMBER_TYPE = auto()
    STRING_TYPE = auto()
    SET = auto()
    TO = auto()
    AS = auto()
    AT = auto()
    END = auto()
    PRINT = auto()
    INPUT = auto()
    GET = auto()
    DUMP = auto()
    SAVE = auto()
    LOAD = auto()
    PROMPT = auto()
    USING = auto()
    INTO = auto()
    EVAL = auto()
    EXEC = auto()
    READ = auto()
    WRITE = auto()
    JSON = auto()
    IMPORT = auto()
    FROM = auto()
    ALL = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    DO = auto()  # "do 100 times" = simple repeat loop
    IN = auto()
    STEP = auto()
    BREAK = auto()
    CONTINUE = auto()
    STOP = auto()
    DEFINE = auto()
    FUNCTION = auto()
    RETURN = auto()
    CALL = auto()
    CLONE = auto()
    DELETE = auto()
    RESET = auto()
    HIDE = auto()
    SHOW = auto()
    COUNT = auto()
    MOVE = auto()
    PROPERTIES = auto()
    GOTO = auto()
    LOOK = auto()
    CONNECT = auto()
    HELP = auto()
    RANDOM = auto()
    CONFIRM = auto()  # go/yes/confirm - execute pending bulk operation
    REPEAT = auto()   # repeat/:repeat/:r - repeat last substantive command
    LENGTH = auto()
    OF = auto()
    CONTAINS = auto()
    APPEND = auto()
    REMOVE = auto()
    INCREMENT = auto()
    DECREMENT = auto()
    SPLIT = auto()
    SUBSTRING = auto()
    LOWERCASE = auto()
    UPPERCASE = auto()
    TRIM = auto()
    INDEXOF = auto()
    LASTINDEXOF = auto()

    # Event system
    WHEN = auto()
    TRIGGER = auto()
    WITH = auto()
    ON = auto()  # play animation on <target>

    # Sound/music system
    PLAY = auto()
    SOUND = auto()
    MUSIC = auto()

    # Metadata system
    META = auto()

    # Test system (only active when lexer is in test_mode)
    TEST = auto()       # test "name" ... endtest
    ENDTEST = auto()    # endtest - closes test block (allows nested end)
    EXPECT = auto()     # expect <condition>
    SECTION = auto()    # section "core" / "standard" / "full"
    TRY = auto()        # try <command> - capture errors
    SKIP = auto()       # test "x" skip "reason"
    TODO = auto()       # test "x" todo - expected to fail
    EXISTS = auto()     # expect box exists
    VOICE = auto()      # test "x" with voice
    CORRECTION = auto() # expect correction "x" to "y"
    NO = auto()         # expect no correction
    ERROR = auto()      # expect error / expect error contains

    # Comparison operators (multi-word)
    IS = auto()
    EQUAL = auto()
    NOT = auto()
    BELOW = auto()
    ABOVE = auto()

    # Logical operators
    AND = auto()
    OR = auto()

    # Query syntax (Phase 3 - Project Arcade)
    WHERE = auto()      # get all where <condition>
    CONFIRMED = auto()  # destroy confirmed (bulk safety)
    INCLUDING = auto()  # get all including hidden

    # Math operators (expression-based)
    PLUS = auto()
    MINUS = auto()
    TIMES = auto()
    DIVIDED = auto()
    BY = auto()
    MODULO = auto()

    # Stack-based operators
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()

    # Stack manipulation
    DUP = auto()
    SWAP = auto()
    DROP = auto()

    # Property stack operations
    PUSH = auto()
    POP = auto()
    STACK = auto()

    # Other
    IDENTIFIER = auto()
    DOT = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()      # { for interpolation
    RBRACE = auto()      # } for interpolation
    LANGLE = auto()      # <
    RANGLE = auto()      # >
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


class Lexer:
    def __init__(self, source: str, test_mode: bool = False):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.test_mode = test_mode  # When True, enables test keywords
        # Note: Indentation is cosmetic in Rosh - no tracking needed

    def error(self, message: str):
        raise RoshSyntaxError(message, self.line, self.column)

    def current_char(self) -> Optional[str]:
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def peek_char(self, offset: int = 1) -> Optional[str]:
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]

    def advance(self) -> Optional[str]:
        if self.pos >= len(self.source):
            return None
        char = self.source[self.pos]
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def skip_whitespace_inline(self):
        """Skip spaces and tabs, but not newlines"""
        while self.current_char() in (' ', '\t'):
            self.advance()

    def skip_comment(self):
        """Skip comments starting with #"""
        if self.current_char() == '#':
            while self.current_char() and self.current_char() != '\n':
                self.advance()

    def skip_multiline_comment(self, delimiter: str):
        """Skip multiline comments (triple quote or triple hash)"""
        # Skip opening delimiter
        for _ in range(len(delimiter)):
            self.advance()

        # Find closing delimiter
        while self.current_char():
            # Check if we've found the closing delimiter
            if self.peek_ahead(len(delimiter)) == delimiter:
                # Skip closing delimiter
                for _ in range(len(delimiter)):
                    self.advance()
                return
            self.advance()

        # If we get here, we hit EOF without closing delimiter
        self.error(f"Unterminated multiline comment (missing closing {delimiter})")

    def peek_ahead(self, count: int) -> str:
        """Peek ahead 'count' characters without advancing"""
        result = ''
        for i in range(count):
            if self.pos + i < len(self.source):
                result += self.source[self.pos + i]
        return result

    def read_number(self) -> Token:
        """Read a number literal with optional suffix.

        Supports:
        - Bare numbers: 50 (interpreted as percentage for coordinates)
        - Percentage: 50% (explicit percentage)
        - Pixels: 400px or 400 px (explicit pixels)

        Design Decision (2025-12-18):
        Bare numbers for coordinates are percentages (0-100 scale).
        Use 'px' suffix for explicit pixel values.
        """
        start_line, start_col = self.line, self.column
        num_str = ''
        has_dot = False

        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            if self.current_char() == '.':
                if has_dot:
                    self.error("Invalid number: multiple decimal points")
                has_dot = True
            num_str += self.current_char()
            self.advance()

        value = float(num_str) if has_dot else int(num_str)

        # Check for percentage sign: 50%
        if self.current_char() == '%':
            self.advance()
            return Token(TokenType.NUMBER_PERCENT, value, start_line, start_col)

        # Check for pixel suffix: 400px (no space)
        if self.current_char() == 'p' and self.peek_char() == 'x':
            self.advance()  # skip 'p'
            self.advance()  # skip 'x'
            return Token(TokenType.NUMBER_PX, value, start_line, start_col)

        # Check for pixel suffix with space: 400 px
        # Look ahead past whitespace
        saved_pos = self.pos
        saved_line = self.line
        saved_col = self.column

        # Skip any spaces
        while self.current_char() == ' ':
            self.advance()

        if self.current_char() == 'p' and self.peek_char() == 'x':
            # Check it's not part of a longer identifier
            self.advance()  # skip 'p'
            self.advance()  # skip 'x'
            next_char = self.current_char()
            if next_char is None or not (next_char.isalnum() or next_char == '_'):
                return Token(TokenType.NUMBER_PX, value, start_line, start_col)
            # It was part of a longer word, restore position
            self.pos = saved_pos
            self.line = saved_line
            self.column = saved_col
        else:
            # Not 'px', restore position
            self.pos = saved_pos
            self.line = saved_line
            self.column = saved_col

        # Plain number (will be interpreted as percentage for coordinates)
        return Token(TokenType.NUMBER, value, start_line, start_col)

    def read_string(self) -> Token:
        """Read a string literal"""
        start_line, start_col = self.line, self.column
        quote_char = self.current_char()
        self.advance()  # Skip opening quote

        string_val = ''
        while self.current_char() and self.current_char() != quote_char:
            if self.current_char() == '\\':
                self.advance()
                next_char = self.current_char()
                if next_char == 'n':
                    string_val += '\n'
                elif next_char == 't':
                    string_val += '\t'
                elif next_char == '\\':
                    string_val += '\\'
                elif next_char == quote_char:
                    string_val += quote_char
                else:
                    string_val += next_char
                self.advance()
            else:
                string_val += self.current_char()
                self.advance()

        if not self.current_char():
            self.error("Unterminated string")

        self.advance()  # Skip closing quote
        return Token(TokenType.STRING, string_val, start_line, start_col)

    def read_identifier_or_keyword(self) -> Token:
        """Read an identifier or keyword"""
        start_line, start_col = self.line, self.column
        identifier = ''

        while self.current_char() and (self.current_char().isalnum() or self.current_char() in ('_', '-')):
            identifier += self.current_char()
            self.advance()

        # Normalize to lowercase for keyword matching (case-insensitive keywords)
        identifier_lower = identifier.lower()

        # Map keywords to token types
        keyword_map = {
            'create': TokenType.CREATE,
            'make': TokenType.CREATE,  # Alias: "make a banana" = "create a banana"
            'object': TokenType.OBJECT,
            'number': TokenType.NUMBER_TYPE,
            'string': TokenType.STRING_TYPE,
            'set': TokenType.SET,
            'to': TokenType.TO,
            'end': TokenType.END,
            'print': TokenType.PRINT,
            'input': TokenType.INPUT,
            'get': TokenType.GET,
            'dump': TokenType.DUMP,
            'save': TokenType.SAVE,
            'load': TokenType.LOAD,
            'prompt': TokenType.PROMPT,
            'using': TokenType.USING,
            'into': TokenType.INTO,
            'eval': TokenType.EVAL,
            'exec': TokenType.EXEC,
            'read': TokenType.READ,
            'write': TokenType.WRITE,
            'json': TokenType.JSON,
            'import': TokenType.IMPORT,
            'from': TokenType.FROM,
            'all': TokenType.ALL,
            'if': TokenType.IF,
            'then': TokenType.THEN,
            'else': TokenType.ELSE,
            'while': TokenType.WHILE,
            'for': TokenType.FOR,
            'do': TokenType.DO,
            'in': TokenType.IN,
            'step': TokenType.STEP,
            'break': TokenType.BREAK,
            'continue': TokenType.CONTINUE,
            'stop': TokenType.STOP,
            'exit': TokenType.STOP,  # 'exit' is alias for 'stop'
            'define': TokenType.DEFINE,
            'function': TokenType.FUNCTION,
            'return': TokenType.RETURN,
            'call': TokenType.CALL,
            'clone': TokenType.CLONE,
            'delete': TokenType.DELETE,
            'destroy': TokenType.DELETE,  # Alias for delete
            'reset': TokenType.RESET,
            'hide': TokenType.HIDE,
            'show': TokenType.SHOW,
            'count': TokenType.COUNT,
            'move': TokenType.MOVE,
            'properties': TokenType.PROPERTIES,
            'props': TokenType.PROPERTIES,  # Alias for properties
            'goto': TokenType.GOTO,
            'look': TokenType.LOOK,
            'l': TokenType.LOOK,  # Short alias
            'examine': TokenType.LOOK,  # Alias for look
            'ex': TokenType.LOOK,  # Short alias for examine
            # Note: 'x' works in REPL only (not keyword, as x is common variable name)
            'connect': TokenType.CONNECT,
            'link': TokenType.CONNECT,  # Alias
            'help': TokenType.HELP,
            'random': TokenType.RANDOM,
            'confirm': TokenType.CONFIRM,
            'yes': TokenType.CONFIRM,  # Alias for confirm
            'go': TokenType.CONFIRM,   # Alias for confirm (paradigm word)
            # Note: 'y' is handled in CLI only (conflicts with variable name)
            'repeat': TokenType.REPEAT,
            # Note: :repeat and :r work in REPL only (colon is tokenized before keywords)
            'length': TokenType.LENGTH,
            'of': TokenType.OF,
            'contains': TokenType.CONTAINS,
            'append': TokenType.APPEND,
            'remove': TokenType.REMOVE,
            'increment': TokenType.INCREMENT,
            'decrement': TokenType.DECREMENT,
            'split': TokenType.SPLIT,
            'substring': TokenType.SUBSTRING,
            'lowercase': TokenType.LOWERCASE,
            'uppercase': TokenType.UPPERCASE,
            'trim': TokenType.TRIM,
            'indexof': TokenType.INDEXOF,
            'lastindexof': TokenType.LASTINDEXOF,
            'when': TokenType.WHEN,
            'trigger': TokenType.TRIGGER,
            'with': TokenType.WITH,
            'on': TokenType.ON,
            'play': TokenType.PLAY,
            'sound': TokenType.SOUND,
            'music': TokenType.MUSIC,
            'meta': TokenType.META,
            'is': TokenType.IS,
            'equal': TokenType.EQUAL,
            'not': TokenType.NOT,
            'below': TokenType.BELOW,
            'above': TokenType.ABOVE,
            'and': TokenType.AND,
            'or': TokenType.OR,
            'where': TokenType.WHERE,
            'confirmed': TokenType.CONFIRMED,
            'including': TokenType.INCLUDING,
            'plus': TokenType.PLUS,
            'minus': TokenType.MINUS,
            'times': TokenType.TIMES,
            'divided': TokenType.DIVIDED,
            'by': TokenType.BY,
            'modulo': TokenType.MODULO,
            'add': TokenType.ADD,
            'subtract': TokenType.SUBTRACT,
            'multiply': TokenType.MULTIPLY,
            'divide': TokenType.DIVIDE,
            'dup': TokenType.DUP,
            'swap': TokenType.SWAP,
            'drop': TokenType.DROP,
            'push': TokenType.PUSH,
            'pop': TokenType.POP,
            'stack': TokenType.STACK,
            'true': TokenType.TRUE,
            'false': TokenType.FALSE,
            'null': TokenType.NULL,
            'as': TokenType.AS,  # 'as' for type annotations and cloning
            'at': TokenType.AT,  # 'at' for position shorthand (create object at x, y)
            'say': TokenType.PRINT,  # 'say' is alias for 'print' (backwards compat)
        }

        # Test system keywords - only active in test_mode to avoid breaking user programs
        if self.test_mode:
            keyword_map.update({
                'test': TokenType.TEST,
                'endtest': TokenType.ENDTEST,
                'expect': TokenType.EXPECT,
                'section': TokenType.SECTION,
                'try': TokenType.TRY,
                'skip': TokenType.SKIP,
                'todo': TokenType.TODO,
                'exists': TokenType.EXISTS,
                'voice': TokenType.VOICE,
                'correction': TokenType.CORRECTION,
                'no': TokenType.NO,
                'error': TokenType.ERROR,
            })

        token_type = keyword_map.get(identifier_lower, TokenType.IDENTIFIER)

        # Keywords use lowercase (case-insensitive commands)
        # Identifiers preserve original case (for bare print strings, variable names with case)
        if token_type == TokenType.IDENTIFIER:
            value = identifier  # Preserve original case
        else:
            value = identifier_lower  # Keywords are lowercase

        return Token(token_type, value, start_line, start_col)

    def tokenize(self) -> List[Token]:
        """Main tokenization method - indentation is cosmetic"""
        while self.pos < len(self.source):
            char = self.current_char()

            if not char:
                break

            # Skip all whitespace (spaces, tabs) - indentation is cosmetic
            if char in (' ', '\t'):
                self.skip_whitespace_inline()
                continue

            # Handle newlines
            if char == '\n':
                # Only emit NEWLINE if we have tokens and last wasn't NEWLINE
                if self.tokens and self.tokens[-1].type != TokenType.NEWLINE:
                    self.tokens.append(Token(TokenType.NEWLINE, None, self.line, self.column))
                self.advance()
                continue

            # Multiline comments (check before strings and single-line comments)
            if self.peek_ahead(3) == '"""':
                self.skip_multiline_comment('"""')
                continue

            if self.peek_ahead(3) == '###':
                self.skip_multiline_comment('###')
                continue

            # Comments
            if char == '#':
                self.skip_comment()
                continue

            # Numbers
            if char.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Strings
            if char in ('"', "'"):
                self.tokens.append(self.read_string())
                continue

            # Identifiers and keywords
            if char.isalpha() or char == '_':
                self.tokens.append(self.read_identifier_or_keyword())
                continue

            # Punctuation
            if char == '.':
                self.tokens.append(Token(TokenType.DOT, '.', self.line, self.column))
                self.advance()
                continue

            if char == ',':
                self.tokens.append(Token(TokenType.COMMA, ',', self.line, self.column))
                self.advance()
                continue

            # Brackets for lists
            if char == '[':
                self.tokens.append(Token(TokenType.LBRACKET, '[', self.line, self.column))
                self.advance()
                continue

            if char == ']':
                self.tokens.append(Token(TokenType.RBRACKET, ']', self.line, self.column))
                self.advance()
                continue

            # Braces for interpolation in bare print
            if char == '{':
                self.tokens.append(Token(TokenType.LBRACE, '{', self.line, self.column))
                self.advance()
                continue

            if char == '}':
                self.tokens.append(Token(TokenType.RBRACE, '}', self.line, self.column))
                self.advance()
                continue

            # Math operators: + - * /
            if char == '+':
                self.tokens.append(Token(TokenType.PLUS, '+', self.line, self.column))
                self.advance()
                continue

            if char == '-':
                self.tokens.append(Token(TokenType.MINUS, '-', self.line, self.column))
                self.advance()
                continue

            if char == '*':
                self.tokens.append(Token(TokenType.TIMES, '*', self.line, self.column))
                self.advance()
                continue

            if char == '/':
                self.tokens.append(Token(TokenType.DIVIDED, '/', self.line, self.column))
                self.advance()
                continue

            if char == '%':
                self.tokens.append(Token(TokenType.MODULO, '%', self.line, self.column))
                self.advance()
                continue

            # Type annotation colon
            if char == ':':
                self.tokens.append(Token(TokenType.COLON, ':', self.line, self.column))
                self.advance()
                continue

            # Semicolon for command separation
            if char == ';':
                self.tokens.append(Token(TokenType.SEMICOLON, ';', self.line, self.column))
                self.advance()
                continue

            # Angle brackets for generic types (list<string>)
            if char == '<':
                self.tokens.append(Token(TokenType.LANGLE, '<', self.line, self.column))
                self.advance()
                continue

            if char == '>':
                self.tokens.append(Token(TokenType.RANGLE, '>', self.line, self.column))
                self.advance()
                continue

            self.error(f"Unexpected character: {char!r}")

        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))

        return self.tokens
