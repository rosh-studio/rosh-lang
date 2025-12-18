"""
Parser for Rosh - converts tokens into an AST
"""

from typing import List, Optional
from .lexer import Token, TokenType
from .ast_nodes import *
from .errors import RoshSyntaxError


# Reserved words that CANNOT be used as variable/object names
# These are core language features that must be protected
RESERVED_WORDS = {
    # Control flow
    'if', 'then', 'else', 'end', 'while', 'for', 'in', 'step',
    'break', 'continue', 'return',

    # Variable/value management
    'create', 'set', 'to', 'from', 'get', 'push', 'pop', 'delete',

    # Types and literals
    'object', 'number', 'string', 'true', 'false', 'null', 'as',

    # Stack operations (CRITICAL - these must be protected)
    'stack', 'dup', 'swap', 'drop', 'add', 'subtract', 'multiply', 'divide',

    # Operators (in expressions)
    'is', 'not', 'and', 'or', 'equal', 'above', 'below',
    'plus', 'minus', 'times', 'divided', 'by', 'modulo', 'contains',

    # Data operations
    'length', 'of', 'append', 'remove', 'increment', 'decrement',

    # String methods
    'split', 'substring', 'lowercase', 'uppercase', 'trim', 'indexof', 'lastindexof',

    # I/O and persistence
    'print', 'say', 'input', 'dump', 'save', 'load', 'read', 'write', 'json',

    # Functions
    'define', 'function', 'call',

    # Advanced features
    'prompt', 'using', 'into', 'exec', 'eval', 'import', 'random', 'all',

    # Program control
    'stop', 'exit',

    # Note: 'meta' is NOT reserved - it becomes a variable after meta blocks
}


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def error(self, message: str):
        token = self.current_token()
        raise RoshSyntaxError(message, token.line, token.column)

    def validate_identifier(self, name: str, context: str = "variable"):
        """Validate that an identifier is not a reserved word.

        Args:
            name: The identifier name to validate
            context: Description of what the name is for (e.g., "variable", "function parameter")

        Raises:
            RoshSyntaxError if the name is a reserved word
        """
        if name.lower() in RESERVED_WORDS:
            self.error(
                f"Cannot use reserved word '{name}' as {context} name. "
                f"Reserved words are core language features and cannot be redefined."
            )

    def expect_identifier_for(self, context: str = "name") -> Token:
        """Expect an IDENTIFIER token, with helpful error if reserved word is used.

        Args:
            context: What the identifier is being used for (e.g., "variable", "function")

        Returns:
            The IDENTIFIER token

        Raises:
            RoshSyntaxError with clear message if reserved word used or token is not IDENTIFIER
        """
        token = self.current_token()
        if token.type != TokenType.IDENTIFIER:
            # Check if it's a reserved word token
            if token.value and token.value.lower() in RESERVED_WORDS:
                self.error(
                    f"Cannot use reserved word '{token.value}' as {context} name. "
                    f"Reserved words are core language features and cannot be redefined."
                )
            else:
                self.error(f"Expected {context} name, got {token.type.name}")
        return self.advance()

    def current_token(self) -> Token:
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[self.pos]

    def peek_token(self, offset: int = 1) -> Token:
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[pos]

    def advance(self) -> Token:
        token = self.current_token()
        if token.type != TokenType.EOF:
            self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        """Consume a token of the expected type or raise error"""
        token = self.current_token()
        if token.type != token_type:
            self.error(f"Expected {token_type.name}, got {token.type.name}")
        return self.advance()

    def skip_newlines(self):
        """Skip any NEWLINE or SEMICOLON tokens (statement separators)"""
        while self.current_token().type in (TokenType.NEWLINE, TokenType.SEMICOLON):
            self.advance()

    def parse(self) -> Program:
        """Parse the entire program"""
        statements = []
        self.skip_newlines()

        while self.current_token().type != TokenType.EOF:
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()

        return Program(statements=statements)

    def parse_statement(self) -> Optional[ASTNode]:
        """Parse a single statement"""
        self.skip_newlines()
        token = self.current_token()

        if token.type == TokenType.CREATE:
            return self.parse_create()
        elif token.type == TokenType.SET:
            return self.parse_set()
        elif token.type == TokenType.APPEND:
            return self.parse_append()
        elif token.type == TokenType.REMOVE:
            return self.parse_remove()
        elif token.type == TokenType.INCREMENT:
            return self.parse_increment()
        elif token.type == TokenType.DECREMENT:
            return self.parse_decrement()
        elif token.type == TokenType.PUSH:
            return self.parse_push()
        elif token.type == TokenType.POP:
            return self.parse_pop()
        elif token.type == TokenType.STACK:
            return self.parse_stack()
        elif token.type == TokenType.PRINT:
            return self.parse_print()
        elif token.type == TokenType.INPUT:
            return self.parse_input()
        elif token.type == TokenType.GET:
            return self.parse_get()
        elif token.type == TokenType.DUMP:
            return self.parse_dump()
        elif token.type == TokenType.SAVE:
            return self.parse_save()
        elif token.type == TokenType.LOAD:
            return self.parse_load()
        elif token.type == TokenType.PROMPT:
            return self.parse_prompt()
        elif token.type == TokenType.EVAL:
            return self.parse_eval()
        elif token.type == TokenType.READ:
            return self.parse_read()
        elif token.type == TokenType.WRITE:
            return self.parse_write()
        elif token.type == TokenType.IMPORT:
            return self.parse_import()
        elif token.type in (TokenType.ADD, TokenType.SUBTRACT, TokenType.MULTIPLY, TokenType.DIVIDE,
                             TokenType.DUP, TokenType.SWAP, TokenType.DROP):
            return self.parse_stack_op()
        elif token.type == TokenType.IF:
            return self.parse_if()
        elif token.type == TokenType.WHILE:
            return self.parse_while()
        elif token.type == TokenType.FOR:
            return self.parse_for()
        elif token.type == TokenType.WHEN:
            return self.parse_when()
        elif token.type == TokenType.TRIGGER:
            return self.parse_trigger()
        elif token.type == TokenType.PLAY:
            return self.parse_play()
        elif token.type == TokenType.META:
            return self.parse_meta()
        elif token.type == TokenType.DEFINE:
            return self.parse_define()
        elif token.type == TokenType.RETURN:
            return self.parse_return()
        elif token.type == TokenType.BREAK:
            return self.parse_break()
        elif token.type == TokenType.CONTINUE:
            return self.parse_continue()
        elif token.type == TokenType.STOP:
            return self.parse_stop()
        elif token.type == TokenType.CALL:
            return self.parse_call()
        elif token.type == TokenType.CLONE:
            return self.parse_clone()
        elif token.type == TokenType.DELETE:
            return self.parse_delete()
        elif token.type == TokenType.PROPERTIES:
            return self.parse_properties()
        elif token.type == TokenType.GOTO:
            return self.parse_goto()
        elif token.type == TokenType.LOOK:
            return self.parse_look()
        elif token.type == TokenType.CONNECT:
            return self.parse_connect()
        elif token.type == TokenType.HELP:
            return self.parse_help()
        elif token.type in (TokenType.END, TokenType.DEDENT, TokenType.EOF):
            return None
        else:
            self.error(f"Unexpected token: {token.type.name}")

    def parse_create(self) -> ASTNode:
        """Parse: create object <name> ... end  OR  create <name> to <value>  OR  create <template> [name]"""
        line = self.current_token().line
        self.expect(TokenType.CREATE)

        type_token = self.current_token()

        # Handle object creation: create object <name> ... end
        if type_token.type == TokenType.OBJECT:
            self.advance()
            name_token = self.expect_identifier_for("object")
            name = name_token.value

            # Check for 'from parent1, parent2, ...' syntax
            parents = None
            if self.current_token().type == TokenType.FROM:
                self.advance()
                parents = []
                # Parse comma-separated list of parent names
                parents.append(self.expect(TokenType.IDENTIFIER).value)
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    parents.append(self.expect(TokenType.IDENTIFIER).value)

            self.skip_newlines()

            body = []

            # Check for shorthand position syntax: at x, y  OR  at x y
            if self.current_token().type == TokenType.AT:
                self.advance()
                x_token = self.expect(TokenType.NUMBER)
                x_value = Literal(value=x_token.value, type_name='number', line=x_token.line)

                # Accept comma (optional) between coordinates
                if self.current_token().type == TokenType.COMMA:
                    self.advance()

                y_token = self.expect(TokenType.NUMBER)
                y_value = Literal(value=y_token.value, type_name='number', line=y_token.line)

                # Add implicit set x and set y to body
                from .ast_nodes import SetProperty, Identifier
                body.append(SetProperty(
                    target=Identifier(name='x', line=line),
                    value=x_value,
                    line=line
                ))
                body.append(SetProperty(
                    target=Identifier(name='y', line=line),
                    value=y_value,
                    line=line
                ))
                self.skip_newlines()

            # Parse remaining body statements (if any)
            while self.current_token().type not in (TokenType.END, TokenType.EOF):
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
                self.skip_newlines()

            self.expect(TokenType.END)
            self.skip_newlines()

            return CreateObject(name=name, body=body, parents=parents, line=line)

        # Handle legacy typed syntax: create number/string <name> to <value>
        elif type_token.type in (TokenType.NUMBER_TYPE, TokenType.STRING_TYPE):
            type_name = type_token.value
            self.advance()

            name_token = self.expect_identifier_for("variable")
            name = name_token.value

            self.expect(TokenType.TO)

            value_expr = self.parse_expression()

            # Ignore type_name, will be inferred from value
            return CreateValue(type_name=None, name=name, value=value_expr, line=line)

        # Handle identifier - could be:
        # 1. create <name> to <value> (new typeless syntax)
        # 2. create <template> <name> (clone with explicit name)
        # 3. create <template> (anonymous clone)
        elif type_token.type == TokenType.IDENTIFIER:
            name = type_token.value
            self.advance()

            next_token = self.current_token()

            # Check for type annotation: create <name>: <type> to <value> OR create <name> as <type> to <value>
            if next_token.type in (TokenType.COLON, TokenType.AS):
                self.validate_identifier(name, "variable")
                self.advance()  # skip COLON or AS
                annotated_type = self.parse_type_annotation()
                self.expect(TokenType.TO)
                value_expr = self.parse_expression()
                return CreateValue(name=name, value=value_expr, annotated_type=annotated_type, line=line)

            elif next_token.type == TokenType.TO:
                # New syntax: create <name> to <value> (no annotation)
                self.validate_identifier(name, "variable")
                self.advance()  # skip TO
                value_expr = self.parse_expression()
                return CreateValue(name=name, value=value_expr, annotated_type=None, line=line)

            elif next_token.type == TokenType.IDENTIFIER:
                # Clone with explicit target: create <template> <name>
                target = next_token.value
                self.validate_identifier(target, "clone target")
                self.advance()
                return CloneObject(source=name, target=target, line=line)

            else:
                # Anonymous clone: create <template>
                return CloneObject(source=name, target=None, line=line)

        else:
            self.error(f"Expected object, type, or identifier after 'create', got {type_token.type.name}")

    def parse_type_annotation(self):
        """
        Parse a type annotation.

        Supports:
        - Simple types: number, string, boolean, null, object
        - Generic types: list<number>, list<string>, list<any>

        Returns:
        - Simple type: 'number', 'string', etc.
        - Generic type: ('list', 'number'), ('list', 'string'), etc.
        """
        type_token = self.current_token()

        # Check for simple types
        if type_token.type == TokenType.NUMBER_TYPE:
            self.advance()
            return 'number'
        elif type_token.type == TokenType.STRING_TYPE:
            self.advance()
            return 'string'
        elif type_token.type == TokenType.IDENTIFIER:
            type_name = type_token.value.lower()
            self.advance()

            # Check for generic type: list<...>
            if type_name == 'list':
                if self.current_token().type == TokenType.LANGLE:
                    self.advance()  # skip <

                    # Parse element type
                    elem_token = self.current_token()
                    if elem_token.type == TokenType.NUMBER_TYPE:
                        elem_type = 'number'
                        self.advance()
                    elif elem_token.type == TokenType.STRING_TYPE:
                        elem_type = 'string'
                        self.advance()
                    elif elem_token.type == TokenType.IDENTIFIER:
                        elem_type = elem_token.value.lower()
                        self.advance()
                    else:
                        self.error(f"Expected type name after 'list<', got {elem_token.type.name}")

                    self.expect(TokenType.RANGLE)  # expect >
                    return ('list', elem_type)
                else:
                    # Just 'list' without element type - treat as list<any>
                    return ('list', 'any')

            # Other simple types: boolean, null, object, any
            elif type_name in ('boolean', 'bool', 'null', 'object', 'any'):
                return type_name
            else:
                self.error(f"Unknown type: {type_name}")
        else:
            self.error(f"Expected type name, got {type_token.type.name}")

    def parse_set(self):
        """Parse: set <name>: <type> to <value> OR set <name> as <type> to <value> OR set <target> [to] <value>

        Also supports natural language property access:
          set book.color to red   (dot syntax)
          set book color to red   (natural language - equivalent to above)
        """
        line = self.current_token().line
        self.expect(TokenType.SET)

        # Check for type annotation: set x: number to 42 OR set x as number to 42
        if self.current_token().type == TokenType.IDENTIFIER:
            name_token = self.current_token()
            next_token = self.peek_token()

            if next_token.type in (TokenType.COLON, TokenType.AS):
                # Variable creation with type annotation
                self.validate_identifier(name_token.value, "variable")
                self.advance()  # consume identifier
                self.advance()  # consume colon or 'as'

                annotated_type = self.parse_type_annotation()

                self.expect(TokenType.TO)
                value = self.parse_expression()

                return CreateValue(
                    name=name_token.value,
                    value=value,
                    annotated_type=annotated_type,
                    line=line
                )

            # Check for natural language property access: set book color to red
            # Pattern: IDENTIFIER IDENTIFIER TO (where second identifier is property name)
            if next_token.type == TokenType.IDENTIFIER:
                # Peek further to see if there's a TO after the second identifier
                # This distinguishes "set book color to red" from "set x 42" (no to)
                self.advance()  # consume first identifier (object name)
                prop_token = self.current_token()
                after_prop = self.peek_token()

                if after_prop.type == TokenType.TO:
                    # Natural language: set book color to red
                    self.advance()  # consume property name
                    self.advance()  # consume TO
                    value = self.parse_expression()

                    target = PropertyAccess(
                        object=Identifier(name=name_token.value, line=name_token.line),
                        property=prop_token.value,
                        line=prop_token.line
                    )
                    return SetProperty(target=target, value=value, line=line)
                else:
                    # Not natural language syntax, backtrack
                    # Put back the position - we consumed one token too many
                    self.pos -= 1  # go back to first identifier

        # Otherwise parse as normal set/assignment
        target = self.parse_target()

        # 'to' is optional - skip it if present
        if self.current_token().type == TokenType.TO:
            self.advance()

        value = self.parse_expression()

        return SetProperty(target=target, value=value, line=line)

    def parse_append(self):
        """Parse: append <item> to <list>"""
        from .ast_nodes import Append
        line = self.current_token().line
        self.expect(TokenType.APPEND)

        item = self.parse_expression()

        self.expect(TokenType.TO)

        target = self.parse_target()

        return Append(item=item, target=target, line=line)

    def parse_remove(self):
        """Parse: remove <item> from <list>"""
        from .ast_nodes import Remove
        line = self.current_token().line
        self.expect(TokenType.REMOVE)

        item = self.parse_expression()

        self.expect(TokenType.FROM)

        target = self.parse_target()

        return Remove(item=item, target=target, line=line)

    def parse_increment(self):
        """Parse: increment <variable>"""
        from .ast_nodes import Increment
        line = self.current_token().line
        self.expect(TokenType.INCREMENT)

        target = self.parse_target()

        return Increment(target=target, line=line)

    def parse_decrement(self):
        """Parse: decrement <variable>"""
        from .ast_nodes import Decrement
        line = self.current_token().line
        self.expect(TokenType.DECREMENT)

        target = self.parse_target()

        return Decrement(target=target, line=line)

    def parse_push(self):
        """Parse: push <target> <value>"""
        from .ast_nodes import PushProperty
        line = self.current_token().line
        self.expect(TokenType.PUSH)

        target = self.parse_target()

        value = self.parse_expression()

        return PushProperty(target=target, value=value, line=line)

    def parse_pop(self):
        """Parse: pop <target>"""
        from .ast_nodes import PopProperty
        line = self.current_token().line
        self.expect(TokenType.POP)

        target = self.parse_target()

        return PopProperty(target=target, line=line)

    def parse_stack(self):
        """Parse: stack"""
        from .ast_nodes import StackCommand
        line = self.current_token().line
        self.expect(TokenType.STACK)

        return StackCommand(line=line)

    def parse_target(self) -> ASTNode:
        """Parse a target (identifier, property access, or list indexing)"""
        from .ast_nodes import ListIndex
        # Accept both IDENTIFIER and META (meta is usable as identifier in expressions)
        name_token = self.current_token()
        if name_token.type not in (TokenType.IDENTIFIER, TokenType.META):
            self.error(f"Expected identifier, got {name_token.type.name}")
        self.advance()
        target = Identifier(name=name_token.value, line=name_token.line)

        # Handle property access with dots and list indexing with brackets
        while self.current_token().type in (TokenType.DOT, TokenType.LBRACKET):
            if self.current_token().type == TokenType.DOT:
                self.advance()
                prop_token = self.expect(TokenType.IDENTIFIER)
                target = PropertyAccess(object=target, property=prop_token.value, line=prop_token.line)
            elif self.current_token().type == TokenType.LBRACKET:
                line = self.current_token().line
                self.advance()  # consume [

                # Check if this is a slice (contains :) or a simple index
                # Parse the first expression (start of slice or index)
                start_expr = None
                if self.current_token().type != TokenType.COLON:
                    start_expr = self.parse_expression()

                # Check for colon (slice syntax)
                if self.current_token().type == TokenType.COLON:
                    # This is a slice: my_list[start:end]
                    self.advance()  # consume :

                    # Parse end expression (optional)
                    end_expr = None
                    if self.current_token().type != TokenType.RBRACKET:
                        end_expr = self.parse_expression()

                    self.expect(TokenType.RBRACKET)
                    target = ListIndex(list_expr=target, start_expr=start_expr, end_expr=end_expr, is_slice=True, line=line)
                else:
                    # This is a simple index: my_list[index]
                    self.expect(TokenType.RBRACKET)
                    target = ListIndex(list_expr=target, index_expr=start_expr, is_slice=False, line=line)

        return target

    def parse_print(self) -> Print:
        """Parse: print [<expression>] OR print stack"""
        from .ast_nodes import PrintStack
        line = self.current_token().line
        self.expect(TokenType.PRINT)

        # Check for 'print stack' - pops from stack and prints
        if self.current_token().type == TokenType.STACK:
            self.advance()  # consume 'stack'
            return PrintStack(line=line)

        # If no expression, print blank line (empty string)
        if self.current_token().type in (TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.EOF, TokenType.END, TokenType.ELSE):
            return Print(expression=Literal(value="", type_name="string", line=line), line=line)

        # Otherwise print the expression
        expr = self.parse_expression()
        return Print(expression=expr, line=line)

    def parse_input(self):
        """Parse: input <variable_name> [prompt <string>]"""
        from .ast_nodes import Input
        line = self.current_token().line
        self.expect(TokenType.INPUT)

        # Expect a variable name
        if self.current_token().type != TokenType.IDENTIFIER:
            self.error("Expected variable name after 'input'")

        variable_name = self.current_token().value
        self.advance()  # consume variable name

        # Check for optional 'prompt <string>'
        prompt = None
        if self.current_token().type == TokenType.PROMPT:
            self.advance()  # consume 'prompt'
            # Expect a string literal
            if self.current_token().type == TokenType.STRING:
                prompt = self.current_token().value
                self.advance()  # consume string
            else:
                self.error("Expected string after 'prompt'")

        return Input(variable_name=variable_name, prompt=prompt, line=line)

    def parse_get(self) -> Get:
        """Parse: get <target> - pushes value onto stack

        Supports:
        - get player         → gets variable
        - get player.health  → dot notation
        - get player health  → space-separated property access
        - get all ball       → gets all instances of type
        - get ball 5         → gets instance #5
        """
        line = self.current_token().line
        self.expect(TokenType.GET)

        # Check for 'get all <type>'
        get_all = False
        if self.current_token().type == TokenType.ALL:
            get_all = True
            self.advance()

        # Parse the target - could be simple identifier or property chain
        target = self.parse_target()

        # Check for instance index: get ball 5
        instance_index = None
        if self.current_token().type == TokenType.NUMBER:
            num_token = self.advance()
            instance_index = int(num_token.value)

        # Handle space-separated property access: get player health max
        # (only if not using instance syntax)
        if not instance_index and not get_all:
            while self.current_token().type == TokenType.IDENTIFIER:
                prop_token = self.advance()
                target = PropertyAccess(object=target, property=prop_token.value, line=prop_token.line)

        return Get(target=target, instance_index=instance_index, get_all=get_all, line=line)

    def parse_dump(self) -> Dump:
        """Parse: dump - outputs entire state as JSON"""
        line = self.current_token().line
        self.expect(TokenType.DUMP)
        return Dump(line=line)

    def parse_save(self):
        """Parse: save [game [slot]] | save [filepath]

        save game                  - Save to default slot (transpiler)
        save game "adventure1"     - Save to named slot (transpiler)
        save "state.json"          - Save to file (interpreter)
        """
        from .ast_nodes import SaveGame
        line = self.current_token().line
        self.expect(TokenType.SAVE)

        # Check for "save game" syntax
        if (self.current_token().type == TokenType.IDENTIFIER and
            self.current_token().value.lower() == 'game'):
            self.advance()  # consume 'game'
            # Optional slot name
            slot = None
            if self.current_token().type == TokenType.STRING:
                slot = self.current_token().value
                self.advance()
            return SaveGame(slot=slot, line=line)

        # Original file-based save
        filepath_expr = None
        if self.current_token().type in (TokenType.STRING, TokenType.IDENTIFIER):
            filepath_expr = self.parse_expression()

        return Save(filepath=filepath_expr, line=line)

    def parse_load(self):
        """Parse: load [game [slot]] | load [filepath]

        load                       - Load from default file (interpreter)
        load game                  - Load from default slot (transpiler)
        load game "adventure1"     - Load from named slot (transpiler)
        load "state.json"          - Load from file (interpreter)
        """
        from .ast_nodes import LoadGame
        line = self.current_token().line
        self.expect(TokenType.LOAD)

        # Check for "load game" syntax
        if (self.current_token().type == TokenType.IDENTIFIER and
            self.current_token().value.lower() == 'game'):
            self.advance()  # consume 'game'
            # Optional slot name
            slot = None
            if self.current_token().type == TokenType.STRING:
                slot = self.current_token().value
                self.advance()
            return LoadGame(slot=slot, line=line)

        # Original file-based load - filepath is now optional
        filepath_expr = None
        if self.current_token().type in (TokenType.STRING, TokenType.IDENTIFIER):
            filepath_expr = self.parse_expression()

        return Load(filepath=filepath_expr, line=line)

    def parse_prompt(self) -> Prompt:
        """Parse: prompt [exec] <message> [using <vars>] [into <target>]

        Message can be:
        - A quoted string: prompt "create a ball"
        - Unquoted text: prompt create a big blue ball
        """
        from .ast_nodes import Literal
        line = self.current_token().line
        self.expect(TokenType.PROMPT)

        # Check for exec mode
        exec_mode = False
        if self.current_token().type == TokenType.EXEC:
            exec_mode = True
            self.advance()

        # If the next token is a string, parse normally
        if self.current_token().type == TokenType.STRING:
            message_expr = self.parse_expression()
        else:
            # Collect all tokens until using/into/newline/EOF as raw text
            words = []
            stop_types = {TokenType.USING, TokenType.INTO, TokenType.NEWLINE, TokenType.EOF}
            while self.current_token().type not in stop_types:
                words.append(str(self.current_token().value))
                self.advance()
            message_expr = Literal(value=' '.join(words), type_name='string', line=line)

        # Optional: using <var1> <var2> ...
        context_vars = None
        if self.current_token().type == TokenType.USING:
            self.advance()
            context_vars = []
            while self.current_token().type == TokenType.IDENTIFIER:
                context_vars.append(self.current_token().value)
                self.advance()

        # Optional: into <target>
        target = None
        if self.current_token().type == TokenType.INTO:
            self.advance()
            target_token = self.expect(TokenType.IDENTIFIER)
            target = target_token.value

        return Prompt(
            message=message_expr,
            context_vars=context_vars,
            target=target,
            exec_mode=exec_mode,
            line=line
        )

    def parse_eval(self) -> Eval:
        """Parse: eval <code_string>"""
        line = self.current_token().line
        self.expect(TokenType.EVAL)

        # Parse the code expression (should evaluate to a string)
        code_expr = self.parse_expression()

        return Eval(code_expr=code_expr, line=line)

    def parse_read(self) -> Read:
        """Parse: read [json] <filepath> into <target>"""
        line = self.current_token().line
        self.expect(TokenType.READ)

        # Check for 'json' modifier
        parse_json = False
        if self.current_token().type == TokenType.JSON:
            parse_json = True
            self.advance()

        # Parse filepath expression
        filepath_expr = self.parse_expression()

        # Expect 'into'
        self.expect(TokenType.INTO)

        # Expect target variable name
        target_token = self.expect(TokenType.IDENTIFIER)
        target = target_token.value

        return Read(filepath=filepath_expr, target=target, parse_json=parse_json, line=line)

    def parse_write(self) -> Write:
        """Parse: write <value> to <filepath>"""
        line = self.current_token().line
        self.expect(TokenType.WRITE)

        # Parse value expression
        value_expr = self.parse_expression()

        # Expect 'to'
        self.expect(TokenType.TO)

        # Parse filepath expression
        filepath_expr = self.parse_expression()

        return Write(value_expr=value_expr, filepath=filepath_expr, line=line)

    def parse_import(self) -> Import:
        """Parse: import <module_path>"""
        line = self.current_token().line
        self.expect(TokenType.IMPORT)

        # Parse module path (string or identifier)
        module_path_expr = self.parse_expression()

        return Import(module_path=module_path_expr, line=line)

    def parse_stack_op(self) -> StackOp:
        """Parse stack operations: add, subtract, multiply, divide, dup, swap, drop

        Math ops: Pop two values, perform operation, push result
        Manipulation: dup (duplicate TOS), swap (swap top 2), drop (remove TOS)
        """
        line = self.current_token().line
        token = self.current_token()

        operator_map = {
            TokenType.ADD: 'add',
            TokenType.SUBTRACT: 'subtract',
            TokenType.MULTIPLY: 'multiply',
            TokenType.DIVIDE: 'divide',
            TokenType.DUP: 'dup',
            TokenType.SWAP: 'swap',
            TokenType.DROP: 'drop'
        }

        operator = operator_map[token.type]
        self.advance()

        return StackOp(operator=operator, line=line)

    def parse_if(self) -> IfStatement:
        """Parse: if <condition> then ... end  (with optional else)"""
        line = self.current_token().line
        self.expect(TokenType.IF)

        condition = self.parse_condition()

        self.expect(TokenType.THEN)
        self.skip_newlines()

        then_body = []
        while self.current_token().type not in (TokenType.ELSE, TokenType.END, TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                then_body.append(stmt)
            self.skip_newlines()

        else_body = None
        if self.current_token().type == TokenType.ELSE:
            self.advance()
            self.skip_newlines()

            # Check for 'else if' (or 'elif')
            if self.current_token().type == TokenType.IF:
                # Parse the else-if as a nested if statement
                else_if_stmt = self.parse_if()
                else_body = [else_if_stmt]
            else:
                # Regular else block
                else_body = []
                while self.current_token().type not in (TokenType.END, TokenType.EOF):
                    stmt = self.parse_statement()
                    if stmt:
                        else_body.append(stmt)
                    self.skip_newlines()

                self.expect(TokenType.END)
                self.skip_newlines()
                return IfStatement(condition=condition, then_body=then_body, else_body=else_body, line=line)

        # If we parsed an else-if, the nested if already consumed the END
        # If no else, we need to consume the END here
        if else_body is None or (else_body and not isinstance(else_body[0], IfStatement)):
            self.expect(TokenType.END)
            self.skip_newlines()

        return IfStatement(condition=condition, then_body=then_body, else_body=else_body, line=line)

    def parse_while(self):
        """Parse: while <condition> then ... end"""
        from .ast_nodes import WhileLoop
        line = self.current_token().line
        self.expect(TokenType.WHILE)

        condition = self.parse_condition()

        self.expect(TokenType.THEN)
        self.skip_newlines()

        body = []
        while self.current_token().type not in (TokenType.END, TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()

        self.expect(TokenType.END)
        self.skip_newlines()

        return WhileLoop(condition=condition, body=body, line=line)

    def parse_for(self):
        """Parse for loops in various forms:

        Range loop: for <var> in <start> to <end> [step <step>] then ... end
        List iteration: for <var> in <list_expr> then ... end
        Object collection: for <var> in all <type> then ... end

        Examples:
            for i in 1 to 10 then ... end
            for i in 1 to 10 step 2 then ... end
            for item in my_list then ... end
            for obj in all items then ... end
        """
        from .ast_nodes import ForLoop
        line = self.current_token().line
        self.expect(TokenType.FOR)

        # Get loop variable name
        var_token = self.expect_identifier_for("loop variable")
        variable = var_token.value

        self.expect(TokenType.IN)

        # Check for "all" keyword (iterate over collection)
        if self.current_token().type == TokenType.ALL:
            self.advance()  # consume 'all'
            collection = self.parse_expression()
            self.expect(TokenType.THEN)
            self.skip_newlines()

            body = []
            while self.current_token().type not in (TokenType.END, TokenType.EOF):
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
                self.skip_newlines()

            self.expect(TokenType.END)
            self.skip_newlines()

            return ForLoop(
                variable=variable,
                start=collection,
                end=None,
                step=None,
                body=body,
                is_collection=True,
                line=line
            )

        # Check if it's a list iteration: for item in my_list then
        # vs range-based: for i in 1 to 10 then
        start = self.parse_expression()

        # If next token is THEN, it's list iteration
        if self.current_token().type == TokenType.THEN:
            self.advance()  # consume 'then'
            self.skip_newlines()

            body = []
            while self.current_token().type not in (TokenType.END, TokenType.EOF):
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
                self.skip_newlines()

            self.expect(TokenType.END)
            self.skip_newlines()

            return ForLoop(
                variable=variable,
                start=start,  # This is the list expression
                end=None,
                step=None,
                body=body,
                is_collection=True,  # Treat as collection iteration
                line=line
            )

        # Range-based loop: for i in 1 to 10 [step 2]
        self.expect(TokenType.TO)
        end = self.parse_expression()

        # Optional step
        step = None
        if self.current_token().type == TokenType.STEP:
            self.advance()  # consume 'step'
            step = self.parse_expression()

        self.expect(TokenType.THEN)
        self.skip_newlines()

        body = []
        while self.current_token().type not in (TokenType.END, TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()

        self.expect(TokenType.END)
        self.skip_newlines()

        return ForLoop(
            variable=variable,
            start=start,
            end=end,
            step=step,
            body=body,
            is_collection=False,
            line=line
        )

    def parse_when(self):
        """Parse: when <event_name> [param1 param2 ...] then ... end

        Examples:
            when player_died then ... end
            when combat_start attacker defender then ... end
        """
        from .ast_nodes import WhenStatement
        line = self.current_token().line
        self.expect(TokenType.WHEN)

        # Get event name
        event_token = self.expect_identifier_for("event name")
        event_name = event_token.value

        # Parse optional parameters (until 'then')
        parameters = []
        while self.current_token().type not in (TokenType.THEN, TokenType.EOF):
            param_token = self.expect_identifier_for("event parameter")
            parameters.append(param_token.value)

        self.expect(TokenType.THEN)
        self.skip_newlines()

        # Parse body
        body = []
        while self.current_token().type not in (TokenType.END, TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()

        self.expect(TokenType.END)
        self.skip_newlines()

        return WhenStatement(
            event_name=event_name,
            parameters=parameters,
            body=body,
            line=line
        )

    def parse_trigger(self):
        """Parse: trigger <event_name> [with arg1, arg2, ...]

        Examples:
            trigger player_died
            trigger combat_start with goblin player
        """
        from .ast_nodes import TriggerEvent
        line = self.current_token().line
        self.expect(TokenType.TRIGGER)

        # Get event name
        event_token = self.expect_identifier_for("event name")
        event_name = event_token.value

        # Parse optional arguments after 'with'
        arguments = []
        if self.current_token().type == TokenType.WITH:
            self.advance()  # consume 'with'

            # Parse arguments (expressions separated by nothing or comma)
            # Continue until we hit newline, semicolon, or EOF
            while self.current_token().type not in (TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.EOF):
                # Skip optional commas
                if self.current_token().type == TokenType.COMMA:
                    self.advance()
                    continue

                # Parse argument expression
                arg = self.parse_expression()
                arguments.append(arg)

        self.skip_newlines()

        return TriggerEvent(
            event_name=event_name,
            arguments=arguments,
            line=line
        )

    def parse_play(self):
        """Parse: play sound "filename" OR play music "filename" OR stop music

        Examples:
            play sound "shoot.wav"
            play music "background.mp3"
            stop music
        """
        from .ast_nodes import PlaySound, PlayMusic, StopMusic
        line = self.current_token().line
        self.expect(TokenType.PLAY)

        next_token = self.current_token()

        if next_token.type == TokenType.SOUND:
            self.advance()  # consume 'sound'
            filename_token = self.expect(TokenType.STRING)
            return PlaySound(filename=filename_token.value, line=line)

        elif next_token.type == TokenType.MUSIC:
            self.advance()  # consume 'music'
            filename_token = self.expect(TokenType.STRING)
            return PlayMusic(filename=filename_token.value, line=line)

        else:
            self.error(f"Expected 'sound' or 'music' after 'play', got {next_token.type.name}")

    def parse_meta(self):
        """Parse: meta [.scope] ... end

        Examples:
            meta
                version "1.0.0"
                author "rdubar"
            end

            meta.generated
                uuid "550e8400..."
                checksum "sha256:abc..."
            end

            meta.game
                type "2D"
                engine "phaser"
            end
        """
        from .ast_nodes import Metadata
        line = self.current_token().line
        self.expect(TokenType.META)

        # Check for optional scope (meta.generated, meta.game, etc.)
        scope = None
        if self.current_token().type == TokenType.DOT:
            self.advance()  # consume dot
            scope_token = self.expect_identifier_for("metadata scope")
            scope = scope_token.value

        self.skip_newlines()

        # Parse key-value pairs until 'end'
        fields = {}
        while self.current_token().type not in (TokenType.END, TokenType.EOF):
            # Skip newlines between fields
            if self.current_token().type == TokenType.NEWLINE:
                self.advance()
                continue

            # Parse key (identifier)
            key_token = self.expect_identifier_for("metadata key")
            key = key_token.value

            # Parse value (expression)
            value_expr = self.parse_expression()

            # Store in fields dictionary
            fields[key] = value_expr

            self.skip_newlines()

        self.expect(TokenType.END)
        self.skip_newlines()

        return Metadata(
            scope=scope,
            fields=fields,
            line=line
        )

    def parse_condition(self) -> ASTNode:
        """Parse a condition (with comparisons and logical operators)"""
        from .ast_nodes import LogicalOp

        # Parse the first condition term (may have NOT prefix)
        result = self.parse_condition_term()

        # Handle AND/OR infix operators
        while self.current_token().type in (TokenType.AND, TokenType.OR):
            op_token = self.advance()
            operator = op_token.value  # 'and' or 'or'
            # Parse the right side (which can also have NOT prefix)
            right = self.parse_condition_term()
            result = LogicalOp(operator=operator, left=result, right=right, line=op_token.line)

        return result

    def parse_condition_term(self) -> ASTNode:
        """Parse a condition term (comparison with optional NOT prefix)"""
        from .ast_nodes import LogicalOp

        # Handle NOT prefix operator
        if self.current_token().type == TokenType.NOT:
            line = self.current_token().line
            self.advance()
            operand = self.parse_comparison()
            return LogicalOp(operator='not', right=operand, line=line)
        else:
            return self.parse_comparison()

    def parse_comparison(self) -> ASTNode:
        """Parse a comparison expression"""
        left = self.parse_expression()

        # Handle 'is' comparisons
        if self.current_token().type == TokenType.IS:
            self.advance()

            # Check for 'is not'
            if self.current_token().type == TokenType.NOT:
                self.advance()
                self.expect(TokenType.EQUAL)
                self.expect(TokenType.TO)
                right = self.parse_expression()
                return Comparison(left=left, operator='not_equal', right=right, line=left.line)

            # Check for 'is equal to'
            if self.current_token().type == TokenType.EQUAL:
                self.advance()
                self.expect(TokenType.TO)
                right = self.parse_expression()
                return Comparison(left=left, operator='equal', right=right, line=left.line)

            # Check for 'is below'
            if self.current_token().type == TokenType.BELOW:
                self.advance()
                right = self.parse_expression()
                return Comparison(left=left, operator='below', right=right, line=left.line)

            # Check for 'is above'
            if self.current_token().type == TokenType.ABOVE:
                self.advance()
                right = self.parse_expression()
                return Comparison(left=left, operator='above', right=right, line=left.line)

        # Handle 'contains'
        if self.current_token().type == TokenType.CONTAINS:
            from .ast_nodes import Contains
            line = self.current_token().line
            self.advance()  # consume 'contains'
            item = self.parse_expression()
            return Contains(container=left, item=item, line=line)

        return left

    def parse_define(self) -> FunctionDef:
        """Parse: define function <name> <params> ... end"""
        line = self.current_token().line
        self.expect(TokenType.DEFINE)
        self.expect(TokenType.FUNCTION)

        name_token = self.expect_identifier_for("function")
        name = name_token.value

        # Parse parameters (simple list of identifiers)
        parameters = []
        while True:
            token = self.current_token()
            # Check if we hit end of parameter list
            if token.type in (TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.EOF):
                break
            # Check for reserved word being used as parameter
            if token.value and token.value.lower() in RESERVED_WORDS and token.type != TokenType.IDENTIFIER:
                self.error(
                    f"Cannot use reserved word '{token.value}' as function parameter name. "
                    f"Reserved words are core language features and cannot be redefined."
                )
            # Must be an identifier
            if token.type != TokenType.IDENTIFIER:
                break
            param_token = self.advance()
            parameters.append(param_token.value)

        self.skip_newlines()

        body = []
        while self.current_token().type not in (TokenType.END, TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()

        self.expect(TokenType.END)
        self.skip_newlines()

        return FunctionDef(name=name, parameters=parameters, body=body, line=line)

    def parse_return(self):
        """Parse: return [expression]"""
        from .ast_nodes import Return
        line = self.current_token().line
        self.expect(TokenType.RETURN)

        # Check if there's an expression to return
        token = self.current_token()
        if token.type in (TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.NUMBER_PX,
                         TokenType.NUMBER_PERCENT, TokenType.STRING,
                         TokenType.TRUE, TokenType.FALSE, TokenType.NULL, TokenType.MINUS):
            value = self.parse_expression()
        else:
            value = None

        return Return(value=value, line=line)

    def parse_break(self):
        """Parse: break"""
        from .ast_nodes import Break
        line = self.current_token().line
        self.expect(TokenType.BREAK)
        return Break(line=line)

    def parse_continue(self):
        """Parse: continue"""
        from .ast_nodes import Continue
        line = self.current_token().line
        self.expect(TokenType.CONTINUE)
        return Continue(line=line)

    def parse_stop(self):
        """Parse: stop OR stop music"""
        from .ast_nodes import Stop, StopMusic
        line = self.current_token().line
        self.expect(TokenType.STOP)

        # Check if this is "stop music"
        if self.current_token().type == TokenType.MUSIC:
            self.advance()  # consume 'music'
            return StopMusic(line=line)

        # Otherwise it's just "stop" (program termination)
        return Stop(line=line)

    def parse_call(self) -> FunctionCall:
        """Parse: call <name> <args>"""
        line = self.current_token().line
        self.expect(TokenType.CALL)

        name_token = self.expect(TokenType.IDENTIFIER)
        name = name_token.value

        # Parse arguments (simple expressions)
        arguments = []
        while self.current_token().type in (TokenType.IDENTIFIER, TokenType.NUMBER,
                                             TokenType.NUMBER_PX, TokenType.NUMBER_PERCENT,
                                             TokenType.STRING, TokenType.TRUE,
                                             TokenType.FALSE, TokenType.NULL, TokenType.MINUS):
            arg = self.parse_expression()
            arguments.append(arg)

        return FunctionCall(name=name, arguments=arguments, line=line)

    def parse_clone(self) -> CloneObject:
        """Parse: clone <source> as <target>"""
        line = self.current_token().line
        self.expect(TokenType.CLONE)

        source_token = self.expect(TokenType.IDENTIFIER)
        source = source_token.value

        # Accept both 'as' and 'to'
        if self.current_token().type not in (TokenType.AS, TokenType.TO):
            self.error(f"Expected 'as' or 'to', got {self.current_token().type.name}")
        self.advance()

        target_token = self.expect(TokenType.IDENTIFIER)
        target = target_token.value

        return CloneObject(source=source, target=target, line=line)

    def parse_delete(self) -> DeleteObject:
        """Parse: delete <name>"""
        line = self.current_token().line
        self.expect(TokenType.DELETE)

        name_token = self.expect(TokenType.IDENTIFIER)
        name = name_token.value

        return DeleteObject(name=name, line=line)

    def parse_properties(self) -> PropertiesCommand:
        """Parse: properties <name> or props <name>"""
        line = self.current_token().line
        self.expect(TokenType.PROPERTIES)

        target_token = self.expect(TokenType.IDENTIFIER)
        target = target_token.value

        return PropertiesCommand(target=target, line=line)

    def parse_goto(self):
        """Parse goto commands:
        - goto <room>                    # legacy room navigation
        - goto scene <name>              # change scene
        - goto level <number>            # change level
        - goto scene <name> level <n>    # change both
        """
        line = self.current_token().line
        self.expect(TokenType.GOTO)

        next_token = self.current_token()

        # Check for "goto scene" or "goto level"
        if next_token.type == TokenType.IDENTIFIER:
            keyword = next_token.value.lower()

            if keyword == "scene":
                self.advance()  # consume "scene"
                scene_token = self.expect(TokenType.IDENTIFIER)
                scene_name = scene_token.value

                # Check for optional "level <n>"
                level_num = None
                if (self.current_token().type == TokenType.IDENTIFIER and
                    self.current_token().value.lower() == "level"):
                    self.advance()  # consume "level"
                    level_token = self.expect(TokenType.NUMBER)
                    level_num = int(level_token.value)

                return GotoScene(scene=scene_name, level=level_num, line=line)

            elif keyword == "level":
                self.advance()  # consume "level"
                level_token = self.expect(TokenType.NUMBER)
                level_num = int(level_token.value)

                return GotoScene(scene=None, level=level_num, line=line)

            else:
                # Legacy: goto <room>
                room = next_token.value
                self.advance()
                return GotoRoom(room=room, line=line)

        # Fallback: expect identifier for room name
        room_token = self.expect(TokenType.IDENTIFIER)
        return GotoRoom(room=room_token.value, line=line)

    def parse_look(self) -> LookCommand:
        """Parse: look [object] - Show current room or examine object"""
        line = self.current_token().line
        self.expect(TokenType.LOOK)

        # Optional target object
        target = None
        if self.current_token().type == TokenType.IDENTIFIER:
            target_token = self.advance()
            target = target_token.value

        return LookCommand(target=target, line=line)

    def parse_connect(self) -> ConnectRooms:
        """Parse: connect <room1> <direction> [to] <room2>"""
        line = self.current_token().line
        self.expect(TokenType.CONNECT)

        room1_token = self.expect(TokenType.IDENTIFIER)
        room1 = room1_token.value

        direction_token = self.expect(TokenType.IDENTIFIER)
        direction = direction_token.value

        # 'to' is optional
        if self.current_token().type == TokenType.TO:
            self.advance()

        room2_token = self.expect(TokenType.IDENTIFIER)
        room2 = room2_token.value

        return ConnectRooms(room1=room1, direction=direction, room2=room2, line=line)

    def parse_help(self) -> Help:
        """Parse: help [topic] - Display help"""
        line = self.current_token().line
        self.expect(TokenType.HELP)

        # Optional topic - accept identifiers or keywords
        topic = None
        current = self.current_token()
        if current.type not in (TokenType.NEWLINE, TokenType.EOF):
            topic_token = self.advance()
            # Get the string representation of the topic
            if hasattr(topic_token, 'value') and topic_token.value:
                topic = str(topic_token.value)
            else:
                # For keyword tokens, use the lowercase token name
                topic = topic_token.type.name.lower()

        return Help(topic=topic, line=line)

    def parse_expression(self) -> ASTNode:
        """Parse an expression (with binary operators)"""
        left = self.parse_primary()

        # Handle binary operators
        while self.current_token().type in (TokenType.PLUS, TokenType.MINUS,
                                             TokenType.TIMES, TokenType.DIVIDED, TokenType.MODULO):
            op_token = self.advance()

            if op_token.type == TokenType.DIVIDED:
                self.expect(TokenType.BY)
                operator = 'divided_by'
            elif op_token.type == TokenType.MODULO:
                operator = 'modulo'
            else:
                operator = op_token.value

            right = self.parse_primary()
            left = BinaryOp(left=left, operator=operator, right=right, line=op_token.line)

        return left

    def parse_list_literal(self):
        """Parse: [1, 2, 3] or []"""
        from .ast_nodes import ListLiteral
        line = self.current_token().line
        self.expect(TokenType.LBRACKET)

        elements = []
        # Handle empty list
        if self.current_token().type == TokenType.RBRACKET:
            self.advance()
            return ListLiteral(elements=elements, line=line)

        # Parse first element
        elements.append(self.parse_expression())

        # Parse remaining elements
        while self.current_token().type == TokenType.COMMA:
            self.advance()  # consume comma
            # Allow trailing comma
            if self.current_token().type == TokenType.RBRACKET:
                break
            elements.append(self.parse_expression())

        self.expect(TokenType.RBRACKET)
        return ListLiteral(elements=elements, line=line)

    def parse_random(self):
        """Parse: random or random 1 to 6"""
        from .ast_nodes import Random
        line = self.current_token().line
        self.expect(TokenType.RANDOM)

        # Check if there's a range (min to max)
        if self.current_token().type in (TokenType.NUMBER, TokenType.NUMBER_PX, TokenType.NUMBER_PERCENT):
            min_val = self.parse_primary()  # Parse min value

            if self.current_token().type == TokenType.TO:
                self.advance()  # consume 'to'
                max_val = self.parse_primary()  # Parse max value
                return Random(min_val=min_val, max_val=max_val, line=line)
            else:
                self.error("Expected 'to' after random minimum value")

        # Just 'random' with no arguments - returns 0.0 to 1.0
        return Random(line=line)

    def parse_length(self):
        """Parse: length of <expression>"""
        from .ast_nodes import Length
        line = self.current_token().line
        self.expect(TokenType.LENGTH)

        # Expect 'of'
        if self.current_token().type != TokenType.OF:
            self.error("Expected 'of' after 'length'")
        self.advance()  # consume 'of'

        # Parse the target expression
        target = self.parse_primary()
        return Length(target=target, line=line)

    def parse_split(self):
        """Parse: split <text> by <delimiter>"""
        from .ast_nodes import StringMethod
        line = self.current_token().line
        self.expect(TokenType.SPLIT)

        # Parse the text expression
        target = self.parse_expression()

        # Expect 'by'
        if self.current_token().type != TokenType.BY:
            self.error("Expected 'by' after 'split <text>'")
        self.advance()  # consume 'by'

        # Parse delimiter
        delimiter = self.parse_expression()
        return StringMethod(method='split', target=target, args=[delimiter], line=line)

    def parse_substring(self):
        """Parse: substring of <text> from <start> length <len>"""
        from .ast_nodes import StringMethod
        line = self.current_token().line
        self.expect(TokenType.SUBSTRING)

        # Expect 'of'
        if self.current_token().type != TokenType.OF:
            self.error("Expected 'of' after 'substring'")
        self.advance()  # consume 'of'

        # Parse the text expression
        target = self.parse_primary()

        # Expect 'from'
        if self.current_token().type != TokenType.FROM:
            self.error("Expected 'from' after 'substring of <text>'")
        self.advance()  # consume 'from'

        # Parse start position
        start = self.parse_expression()

        # Expect 'length'
        if self.current_token().type != TokenType.LENGTH:
            self.error("Expected 'length' after 'substring of <text> from <start>'")
        self.advance()  # consume 'length'

        # Parse length
        length = self.parse_expression()
        return StringMethod(method='substring', target=target, args=[start, length], line=line)

    def parse_lowercase(self):
        """Parse: lowercase of <text>"""
        from .ast_nodes import StringMethod
        line = self.current_token().line
        self.expect(TokenType.LOWERCASE)

        # Expect 'of'
        if self.current_token().type != TokenType.OF:
            self.error("Expected 'of' after 'lowercase'")
        self.advance()  # consume 'of'

        # Parse the text expression
        target = self.parse_primary()
        return StringMethod(method='lowercase', target=target, args=[], line=line)

    def parse_uppercase(self):
        """Parse: uppercase of <text>"""
        from .ast_nodes import StringMethod
        line = self.current_token().line
        self.expect(TokenType.UPPERCASE)

        # Expect 'of'
        if self.current_token().type != TokenType.OF:
            self.error("Expected 'of' after 'uppercase'")
        self.advance()  # consume 'of'

        # Parse the text expression
        target = self.parse_primary()
        return StringMethod(method='uppercase', target=target, args=[], line=line)

    def parse_trim(self):
        """Parse: trim <text>"""
        from .ast_nodes import StringMethod
        line = self.current_token().line
        self.expect(TokenType.TRIM)

        # Parse the text expression
        target = self.parse_expression()
        return StringMethod(method='trim', target=target, args=[], line=line)

    def parse_indexof(self):
        """Parse: indexOf <search> in <text>"""
        from .ast_nodes import StringMethod
        line = self.current_token().line
        self.expect(TokenType.INDEXOF)

        # Parse search string
        search = self.parse_expression()

        # Expect 'in'
        if self.current_token().type != TokenType.IN:
            self.error("Expected 'in' after 'indexOf <search>'")
        self.advance()  # consume 'in'

        # Parse the text expression
        target = self.parse_expression()
        return StringMethod(method='indexOf', target=target, args=[search], line=line)

    def parse_lastindexof(self):
        """Parse: lastIndexOf <search> in <text>"""
        from .ast_nodes import StringMethod
        line = self.current_token().line
        self.expect(TokenType.LASTINDEXOF)

        # Parse search string
        search = self.parse_expression()

        # Expect 'in'
        if self.current_token().type != TokenType.IN:
            self.error("Expected 'in' after 'lastIndexOf <search>'")
        self.advance()  # consume 'in'

        # Parse the text expression
        target = self.parse_expression()
        return StringMethod(method='lastIndexOf', target=target, args=[search], line=line)

    def parse_primary(self) -> ASTNode:
        """Parse a primary expression (literal, identifier, or property access)"""
        from .ast_nodes import UnaryOp
        token = self.current_token()

        # Handle unary minus
        if token.type == TokenType.MINUS:
            line = token.line
            self.advance()  # consume '-'
            operand = self.parse_primary()  # Parse the operand
            return UnaryOp(operator='minus', operand=operand, line=line)

        if token.type == TokenType.NUMBER:
            self.advance()
            return Literal(value=token.value, type_name='number', line=token.line)

        elif token.type == TokenType.NUMBER_PX:
            # Pixel value: 400px - store as number with 'pixel' type
            self.advance()
            return Literal(value=token.value, type_name='pixel', line=token.line)

        elif token.type == TokenType.NUMBER_PERCENT:
            # Percentage value: 50% - store as number with 'percentage' type
            self.advance()
            return Literal(value=token.value, type_name='percentage', line=token.line)

        elif token.type == TokenType.STRING:
            self.advance()
            return Literal(value=token.value, type_name='string', line=token.line)

        elif token.type == TokenType.TRUE:
            self.advance()
            return Literal(value=True, type_name='boolean', line=token.line)

        elif token.type == TokenType.FALSE:
            self.advance()
            return Literal(value=False, type_name='boolean', line=token.line)

        elif token.type == TokenType.NULL:
            self.advance()
            return Literal(value=None, type_name='null', line=token.line)

        elif token.type == TokenType.LBRACKET:
            return self.parse_list_literal()

        elif token.type == TokenType.RANDOM:
            return self.parse_random()

        elif token.type == TokenType.LENGTH:
            return self.parse_length()

        elif token.type == TokenType.SPLIT:
            return self.parse_split()

        elif token.type == TokenType.SUBSTRING:
            return self.parse_substring()

        elif token.type == TokenType.LOWERCASE:
            return self.parse_lowercase()

        elif token.type == TokenType.UPPERCASE:
            return self.parse_uppercase()

        elif token.type == TokenType.TRIM:
            return self.parse_trim()

        elif token.type == TokenType.INDEXOF:
            return self.parse_indexof()

        elif token.type == TokenType.LASTINDEXOF:
            return self.parse_lastindexof()

        elif token.type == TokenType.CALL:
            return self.parse_call()

        elif token.type == TokenType.IDENTIFIER:
            return self.parse_target()

        elif token.type == TokenType.META:
            # 'meta' can be used as an identifier in expressions (after meta block creates it)
            return self.parse_target()

        else:
            self.error(f"Unexpected token in expression: {token.type.name}")
