"""
Rosh Interpreter - executes the AST
"""

import sys
import json
import math
import random
import re
import copy
from contextlib import contextmanager
from typing import Any, List, Callable, Optional
from .ast_nodes import *
from .environment import Environment
from .values import RoshObject, RoshFunction, rosh_to_python, is_truthy
from .errors import RoshRuntimeError, RoshTypeError, RoshNameError
from .config import get_config
from .ai_provider import get_provider


# Built-in native functions
BUILTIN_FUNCTIONS: dict[str, Callable] = {
    # Math functions
    'sqrt': lambda x: math.sqrt(x),
    'abs': lambda x: abs(x),
    'pow': lambda x, y: math.pow(x, y),
    'min': lambda *args: min(args),
    'max': lambda *args: max(args),
    'floor': lambda x: math.floor(x),
    'ceil': lambda x: math.ceil(x),
    'round': lambda x: round(x),

    # Trigonometry
    'sin': lambda x: math.sin(x),
    'cos': lambda x: math.cos(x),
    'tan': lambda x: math.tan(x),

    # Random
    'random': lambda: random.random(),
    'randint': lambda a, b: random.randint(int(a), int(b)),

    # Type checking functions
    'is_number': lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
    'is_string': lambda x: isinstance(x, str),
    'is_list': lambda x: isinstance(x, list),
    'is_object': lambda x: isinstance(x, RoshObject),
    'is_null': lambda x: x is None,
    'is_boolean': lambda x: isinstance(x, bool),
}


class Interpreter:
    """
    AST walker that executes Rosh programs
    """

    def __init__(self, output_stream=None, test_mode=False, test_inputs=None, interactive=False):
        from .color import get_color_output

        self.global_env = Environment()
        self.current_env = self.global_env
        self.output_stream = output_stream or sys.stdout
        self.color_out = get_color_output(self.output_stream)  # Color output utility
        self.data_stack = []  # Explicit data stack for stack-based operations
        self.help_registry = {}  # Context-aware help system
        self._register_builtin_help()
        self.interactive = interactive  # Show feedback in REPL mode

        # Instance tracking for multi-instance support
        self.instances = {}  # type_name -> [obj1, obj2, ...]
        self.uuid_map = {}   # uuid -> object
        self.instance_counters = {}  # type_name -> next_number

        # Event system (v0.0.7+)
        self.event_handlers = {}  # event_name -> [handler1, handler2, ...]

        # Test mode (v0.0.8+)
        self.test_mode = test_mode
        self.test_inputs = test_inputs or []
        self.test_input_index = 0

        # Undo/Redo stacks (CLI + interpreters)
        self.undo_stack = []
        self.redo_stack = []
        self.undo_limit = 100
        self._undo_enabled = False  # Enabled after meta initialization
        self._undo_group = 0  # Group ID for bulk undo - all entries in same group undo together

        # Pending bulk operation (requires confirm/yes to execute)
        self.pending_operation = None  # {'type': 'set_all', 'targets': [...], 'prop': ..., 'value': ...}

        # Last substantive command for repeat functionality
        self.last_command = None  # AST node of last non-utility command

        # Batch operation tracking (for summarized feedback)
        self.batch_creates = {}  # {type_name: count} - tracks creates during loops
        self.batch_mode = False  # True when in a loop, suppresses individual feedback

        # Metadata system (v0.0.8+)
        self.source_code = None  # Original source code (for checksum calculation)
        self.program_metadata = {}  # Metadata by scope: 'core', 'generated', 'game', etc.

        # Security flags (v0.0.4+)
        # Remote imports removed for security (offline-first for VR/AR)

        # Current object context (v0.2.6+) - for contextual set/get commands
        self.current_object = None
        self.current_object_name = None

        # Implicit meta object (v0.2.7+) - always exists, holds game state
        self._init_meta_object()
        self._undo_enabled = True

    def _init_meta_object(self):
        """Initialize the implicit meta object

        The meta object:
        - Always exists
        - Never renders (has no visual properties)
        - Holds game state (meta.level, meta.score, etc.)
        - Supports nested properties (meta.game.title, meta.config.difficulty)
        - Is included in save/load
        - Cannot be created or deleted by user code
        """
        meta = RoshObject(name='meta')
        meta._is_meta = True  # Mark as special meta object
        self.global_env.define('meta', meta)
        self.register_instance(meta, type_name='meta', explicit_name='meta')

    def start_undo_group(self):
        """Start a new undo group. All subsequent push_undo calls share this group."""
        self._undo_group += 1

    def push_undo(self, description: str, inverse: Callable[[], None], redo: Optional[Callable[[], None]] = None):
        """Push an undo entry onto the stack."""
        if not self._undo_enabled or not callable(inverse):
            return
        entry = {
            'description': description or 'change',
            'undo': inverse,
            'redo': redo,
            'group': self._undo_group,
        }
        self.undo_stack.append(entry)
        if len(self.undo_stack) > self.undo_limit:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def perform_undo(self, count: int = 1):
        """Execute one or more undo operations (by group)."""
        if not self.undo_stack:
            self.color_out.warning("Nothing to undo")
            return

        for _ in range(count):
            if not self.undo_stack:
                break

            # Get the group of the most recent entry
            target_group = self.undo_stack[-1].get('group', 0)

            # Collect all entries in this group
            group_entries = []
            while self.undo_stack and self.undo_stack[-1].get('group', 0) == target_group:
                group_entries.append(self.undo_stack.pop())

            # Execute undos (already in reverse order - most recent first)
            undo_count = 0
            first_desc = group_entries[0]['description'] if group_entries else 'change'
            for entry in group_entries:
                try:
                    entry['undo']()
                    undo_count += 1
                    if entry.get('redo'):
                        self.redo_stack.append(entry)
                except Exception as exc:
                    self.color_out.error(f"Undo failed: {exc}")
                    # Put remaining entries back
                    self.undo_stack.append(entry)
                    break

            # Report what was undone
            if undo_count > 1:
                self.color_out.success(f"Undo: {first_desc} ({undo_count} operations)")
            elif undo_count == 1:
                self.color_out.success(f"Undo: {first_desc}")

    def describe_undo_stack(self, limit: int = 5):
        """Print the most recent undo entries."""
        if not self.undo_stack:
            self.color_out.dim("Undo stack is empty")
            return
        self.color_out.print("Recent undo entries:", style="cyan")
        for idx, entry in enumerate(reversed(self.undo_stack[-limit:]), 1):
            self.color_out.dim(f"  #{idx} {entry['description']}")

    def perform_redo(self, count: int = 1):
        """Reapply one or more actions."""
        if not self.redo_stack:
            self.color_out.warning("Nothing to redo")
            return
        steps = max(1, min(count, len(self.redo_stack)))
        for _ in range(steps):
            entry = self.redo_stack.pop()
            if not entry.get('redo'):
                self.color_out.warning(f"No redo available for {entry['description']}")
                continue
            try:
                entry['redo']()
                self.color_out.success(f"Redo: {entry['description']}")
                self.undo_stack.append(entry)
            except Exception as exc:
                self.color_out.error(f"Redo failed: {exc}")
                break

    def describe_redo_stack(self, limit: int = 5):
        """Print redo history."""
        if not self.redo_stack:
            self.color_out.dim("Redo stack is empty")
            return
        self.color_out.print("Pending redo entries:", style="cyan")
        for idx, entry in enumerate(reversed(self.redo_stack[-limit:]), 1):
            self.color_out.dim(f"  #{idx} {entry['description']}")

    @contextmanager
    def suspend_undo(self):
        """Temporarily disable undo stacking (for internal operations)."""
        prev = self._undo_enabled
        self._undo_enabled = False
        try:
            yield
        finally:
            self._undo_enabled = prev

    def _snapshot_value(self, value: Any):
        """Return a snapshot suitable for restoration."""
        if isinstance(value, RoshObject):
            return value
        return copy.deepcopy(value)

    def _snapshot_property_stack(self, obj: RoshObject, prop: str):
        """Capture an object's property stack."""
        return copy.deepcopy(obj.property_stacks.get(prop, []))

    def _restore_property_stack(self, obj: RoshObject, prop: str, stack: List[Any]):
        """Restore an object's property stack."""
        if stack:
            obj.property_stacks[prop] = copy.deepcopy(stack)
        else:
            obj.property_stacks.pop(prop, None)

    def _describe_property_path(self, node) -> str:
        """Render human-readable property path for undo messages."""
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, PropertyAccess):
            return f"{self._describe_property_path(node.object)}.{node.property}"
        return "(property)"

    def _find_env_for_binding(self, name: str) -> Optional[Environment]:
        """Locate the environment that owns the given binding."""
        env = self.current_env
        while env:
            if name in env.bindings:
                return env
            env = env.parent
        return None

    def _detach_object_instance(self, obj: Any):
        """Remove a RoshObject from tracking structures."""
        if not isinstance(obj, RoshObject):
            return
        self.uuid_map.pop(obj.uuid, None)

        candidate_names = []
        if obj.id:
            if '-' in obj.id:
                candidate_names.append(obj.id.rsplit('-', 1)[0])
            candidate_names.append(obj.id)
        candidate_names.append(obj.name)

        for type_name in list(set(candidate_names)):
            if type_name in self.instances:
                self.instances[type_name] = [
                    inst for inst in self.instances[type_name]
                    if inst.uuid != obj.uuid
                ]
                if not self.instances[type_name]:
                    del self.instances[type_name]

    def _attach_object_instance(self, obj: Any):
        """Reattach a RoshObject to tracking structures."""
        if not isinstance(obj, RoshObject):
            return
        self.uuid_map[obj.uuid] = obj
        if obj.id and '-' in obj.id:
            type_name = obj.id.rsplit('-', 1)[0]
        elif obj.id:
            type_name = obj.id
        else:
            type_name = obj.name

        instances = self.instances.setdefault(type_name, [])
        if not any(inst.uuid == obj.uuid for inst in instances):
            instances.append(obj)

    def execute(self, program: Program):
        """Execute a program (list of statements)"""
        for statement in program.statements:
            self.eval_statement(statement)

    def register_instance(self, obj: RoshObject, type_name: str = None, explicit_name: str = None):
        """Register an object instance for tracking

        Args:
            obj: The RoshObject to register
            type_name: The type/template name (e.g., "ball", "room")
            explicit_name: If provided, use this as the object's name (no auto-numbering)
        """
        # Add to UUID map
        self.uuid_map[obj.uuid] = obj

        # Determine type name (use object name if not provided)
        if type_name is None:
            type_name = obj.name

        # If explicit name provided, don't auto-number
        if explicit_name:
            obj.id = explicit_name
            # Still track by type
            if type_name not in self.instances:
                self.instances[type_name] = []
            self.instances[type_name].append(obj)
            return

        # Auto-number anonymous instances
        if type_name not in self.instance_counters:
            self.instance_counters[type_name] = 1

        instance_number = self.instance_counters[type_name]
        self.instance_counters[type_name] += 1

        # Set display ID
        obj.id = f"{type_name}-{instance_number}"

        # Add to instances list
        if type_name not in self.instances:
            self.instances[type_name] = []
        self.instances[type_name].append(obj)

    def get_instance(self, type_name: str, index: int = None):
        """Get instance(s) by type

        Args:
            type_name: The type to look up
            index: Optional 1-based index (e.g., "ball 1" → index=1)

        Returns:
            Single object if index provided, list if not
        """
        if type_name not in self.instances:
            return None

        instances = self.instances[type_name]

        if index is not None:
            # 1-based indexing for users
            if 1 <= index <= len(instances):
                return instances[index - 1]
            return None

        return instances

    def _find_type_with_plural(self, type_name: str) -> str:
        """Find type name with plural-to-singular conversion

        Tries:
        1. Exact match (banana)
        2. Remove trailing 's' (bananas → banana)
        3. Remove trailing 'es' (boxes → box)
        4. Fuzzy match using Levenshtein distance

        Returns the matching type name or None
        """
        # Try exact match first
        if type_name in self.instances:
            return type_name

        # Try removing 's'
        if type_name.endswith('s') and type_name[:-1] in self.instances:
            singular = type_name[:-1]
            self.color_out.warning(f"guessed: {type_name} → {singular}")
            return singular

        # Try removing 'es'
        if type_name.endswith('es') and type_name[:-2] in self.instances:
            singular = type_name[:-2]
            self.color_out.warning(f"guessed: {type_name} → {singular}")
            return singular

        # Try removing 'ies' and adding 'y' (bodies → body)
        if type_name.endswith('ies') and type_name[:-3] + 'y' in self.instances:
            singular = type_name[:-3] + 'y'
            self.color_out.warning(f"guessed: {type_name} → {singular}")
            return singular

        return None

    def _pluralize(self, word: str, count: int) -> str:
        """Pluralize a word based on count.

        Handles common English pluralization rules:
        - banana → bananas
        - box → boxes
        - baby → babies
        - leaf → leaves
        - sheep → sheep (irregular)
        """
        if count == 1:
            return word

        # Irregular plurals (common ones)
        irregulars = {
            'sheep': 'sheep', 'fish': 'fish', 'deer': 'deer',
            'child': 'children', 'person': 'people', 'mouse': 'mice',
            'man': 'men', 'woman': 'women', 'foot': 'feet', 'tooth': 'teeth',
        }
        if word.lower() in irregulars:
            return irregulars[word.lower()]

        # Words ending in consonant + y → ies
        if word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
            return word[:-1] + 'ies'

        # Words ending in s, x, z, ch, sh → es
        if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
            return word + 'es'

        # Words ending in f/fe → ves
        if word.endswith('f'):
            return word[:-1] + 'ves'
        if word.endswith('fe'):
            return word[:-2] + 'ves'

        # Default: add s
        return word + 's'

    def _register_builtin_help(self):
        """Register help text for built-in commands"""
        self.help_registry.update({
            # Core commands
            'create': 'Create objects or values.\n  create object <name> [from <parents>] ... end\n  create number <name> as <value>\n  create string <name> as <value>\n  create <template> <name> - Clone template as new object',
            'set': 'Assign a value to a property.\n  set <target> [to] <value>',
            'get': 'Push a value onto the stack.\n  get <target>',
            'print': 'Display a value.\n  print <expression>  or  print (pops from stack)',

            # Object management
            'clone': 'Clone an object.\n  clone <source> as <target>',
            'delete': 'Delete an object.\n  delete <name>',
            'properties': 'List all properties of an object.\n  properties <name>  (alias: props)',
            'props': 'Alias for properties.\n  props <name>',

            # Stack operations
            'stack': 'View the data stack contents (non-destructive).\n  stack',
            'push': 'Push a value onto a property stack.\n  push <target> <value>',
            'pop': 'Pop a value from a property stack.\n  pop <target>',
            'add': 'Pop two values, add them, push result.\n  5 get\n  3 get\n  add  # pushes 8',
            'subtract': 'Pop two values, subtract them, push result.\n  10 get\n  3 get\n  subtract  # pushes 7',
            'multiply': 'Pop two values, multiply them, push result.\n  6 get\n  7 get\n  multiply  # pushes 42',
            'divide': 'Pop two values, divide them, push result.\n  20 get\n  4 get\n  divide  # pushes 5',
            'dup': 'Duplicate top of stack.\n  10 get\n  dup  # stack now has [10, 10]',
            'swap': 'Swap top two stack values.\n  5 get\n  10 get\n  swap  # stack now has [5, 10]',
            'drop': 'Remove top of stack.\n  10 get\n  drop  # removes 10 from stack',

            # Control flow
            'if': 'Conditional execution.\n  if <condition> then\n    ...\n  else\n    ...\n  end',
            'while': 'Loop while condition is true.\n  while <condition> then\n    ...\n  end',
            'for': 'Loop over a range or collection.\n  for <var> in <start> to <end> then ... end\n  for <var> in <start> to <end> step <step> then ... end\n  for <var> in all <type> then ... end\n  for <item> in <list> then ... end',
            'break': 'Exit a loop early.\n  for i in 1 to 10 then\n    if i is equal to 5 then\n      break\n    end\n  end',
            'continue': 'Skip to next iteration of loop.\n  for i in 1 to 10 then\n    if i is equal to 5 then\n      continue\n    end\n    print i\n  end',
            'return': 'Return a value from a function.\n  define function double x\n    return x times 2\n  end',
            'stop': 'Terminate the program immediately. (Alias: exit)\n  stop',
            'exit': 'Terminate the program immediately. (Alias: stop)\n  exit',

            # Functions
            'define': 'Define a function.\n  define function <name> <params>\n    ...\n  end',
            'call': 'Call a function.\n  call <name> <args>',

            # Lists
            'append': 'Add an item to a list.\n  append <value> to <list>',
            'remove': 'Remove an item from a list.\n  remove <value> from <list>',

            # I/O and modules
            'import': 'Import a module.\n  import <module>  (e.g., import mud)',
            'read': 'Read a file.\n  read <filepath> into <var>\n  read json <filepath> into <var>',
            'write': 'Write to a file.\n  write <value> to <filepath>',
            'save': 'Save state to a JSON file.\n  save <filepath>',
            'eval': 'Evaluate Rosh code from a string.\n  eval <code_string>',

            # Navigation commands
            'goto': 'Move to a space or follow an exit.\n  goto <space>  or  goto <direction>  (alias: go)',
            'go': 'Alias for goto.\n  go <space>  or  go <direction>',
            'look': 'Display current space description.\n  look  (alias: l)',
            'l': 'Alias for look.',
            'connect': 'Connect two spaces bidirectionally.\n  connect <space1> <direction> <space2>  (alias: link)',
            'link': 'Alias for connect.\n  link <space1> <direction> <space2>',

            # AI integration
            'prompt': 'Send a prompt to AI.\n  prompt <message> into <var>\n  prompt exec <message> - Execute AI response as code\n  prompt <message> using <vars> into <var>',

            # System
            'dump': 'Output entire state as JSON.',
            'load': 'Restore state from JSON file.\n  load <filepath>',
            'help': 'Display this help.\n  help  - List all commands\n  help <command>  - Show help for command\n  help <object>  - Show properties of object',

            # String functions
            'split': 'Split a string by delimiter.\n  split <text> by <delimiter>',
            'substring': 'Extract substring.\n  substring of <text> from <start> length <len>',
            'lowercase': 'Convert to lowercase.\n  lowercase of <text>',
            'uppercase': 'Convert to uppercase.\n  uppercase of <text>',
            'trim': 'Remove leading/trailing whitespace.\n  trim <text>',
            'indexOf': 'Find first occurrence of substring.\n  indexOf <substring> in <text>',
            'lastIndexOf': 'Find last occurrence of substring.\n  lastIndexOf <substring> in <text>',

            # Utility functions
            'length': 'Get length of string or list.\n  length of <value>',
            'contains': 'Check if string/list contains value.\n  <container> contains <value>',
            'random': 'Generate random number.\n  random  (0.0-1.0)\n  random <min> to <max>  (inclusive)',

            # Math functions
            'abs': 'Absolute value.\n  call abs <number>',
            'min': 'Minimum of values.\n  call min <n1> <n2> ...',
            'max': 'Maximum of values.\n  call max <n1> <n2> ...',
            'round': 'Round to nearest integer.\n  call round <number>',
            'floor': 'Round down.\n  call floor <number>',
            'ceil': 'Round up.\n  call ceil <number>',
            'sqrt': 'Square root.\n  call sqrt <number>',
            'pow': 'Power.\n  call pow <base> <exponent>',
            'sin': 'Sine.\n  call sin <number>',
            'cos': 'Cosine.\n  call cos <number>',
            'tan': 'Tangent.\n  call tan <number>',
        })

    def register_help(self, topic: str, help_text: str):
        """Register help text for a topic (used by modules)"""
        self.help_registry[topic] = help_text

    def get_state(self) -> dict:
        """Get the entire interpreter state as JSON-serializable dict"""
        def serialize_value(value):
            """Convert Rosh values to JSON-serializable format"""
            if isinstance(value, RoshObject):
                # to_json() now includes _type, _name, _uuid, _id
                return value.to_json()
            elif isinstance(value, RoshFunction):
                # TODO(v0.1.0): Function body serialization
                #   Options:
                #   A) Serialize AST (complex, see docs/FUTURE-IMPROVEMENTS.md)
                #   B) Store source code (simpler)
                #   C) Keep current workaround (re-import modules after load)
                #   Current: Option C (documented workaround)
                return {
                    "_type": "function",
                    "name": value.name,
                    "parameters": value.parameters,
                    "_warning": "Function body not serialized - will not be restored"
                }
            else:
                return value

        # Serialize all variables in global environment
        state = {
            "variables": {},
            "stack": [serialize_value(v) for v in self.data_stack],
            # Include instance tracking (v0.0.4+)
            "instance_counters": dict(self.instance_counters) if hasattr(self, 'instance_counters') else {},
            # Note: instances and uuid_map are rebuilt from variables during load
        }

        for name, binding in self.global_env.bindings.items():
            # bindings store {'value': ..., 'type': ...}, extract the actual value
            value = binding['value'] if isinstance(binding, dict) and 'value' in binding else binding
            state["variables"][name] = serialize_value(value)

        return state

    def eval_statement(self, node: ASTNode) -> Any:
        """Evaluate a statement"""
        # Track last substantive command for repeat functionality
        # Exclude utility commands that shouldn't be repeated
        if not isinstance(node, (Help, Confirm, Repeat)):
            self.last_command = node

        if isinstance(node, CreateObject):
            return self.eval_create_object(node)
        elif isinstance(node, CreateValue):
            return self.eval_create_value(node)
        elif isinstance(node, SetProperty):
            return self.eval_set_property(node)
        elif isinstance(node, SetAll):
            return self.eval_set_all(node)
        elif isinstance(node, Confirm):
            return self.eval_confirm(node)
        elif isinstance(node, Repeat):
            return self.eval_repeat(node)
        elif isinstance(node, BulkOperation):
            return self.eval_bulk_operation(node)
        elif isinstance(node, Append):
            return self.eval_append(node)
        elif isinstance(node, Remove):
            return self.eval_remove(node)
        elif isinstance(node, Increment):
            return self.eval_increment(node)
        elif isinstance(node, Decrement):
            return self.eval_decrement(node)
        elif isinstance(node, PushProperty):
            return self.eval_push_property(node)
        elif isinstance(node, PopProperty):
            return self.eval_pop_property(node)
        elif isinstance(node, StackCommand):
            return self.eval_stack_command(node)
        elif isinstance(node, Print):
            return self.eval_print(node)
        elif isinstance(node, PrintStack):
            return self.eval_print_stack(node)
        elif isinstance(node, Input):
            return self.eval_input(node)
        elif isinstance(node, Get):
            return self.eval_get(node)
        elif isinstance(node, Dump):
            return self.eval_dump(node)
        elif isinstance(node, Save):
            return self.eval_save(node)
        elif isinstance(node, Load):
            return self.eval_load(node)
        elif isinstance(node, Prompt):
            return self.eval_prompt(node)
        elif isinstance(node, Eval):
            return self.eval_eval(node)
        elif isinstance(node, Read):
            return self.eval_read(node)
        elif isinstance(node, Write):
            return self.eval_write(node)
        elif isinstance(node, Import):
            return self.eval_import(node)
        elif isinstance(node, StackOp):
            return self.eval_stack_op(node)
        elif isinstance(node, IfStatement):
            return self.eval_if(node)
        elif isinstance(node, WhileLoop):
            return self.eval_while(node)
        elif isinstance(node, ForLoop):
            return self.eval_for(node)
        elif isinstance(node, WhenStatement):
            return self.eval_when_statement(node)
        elif isinstance(node, TriggerEvent):
            return self.eval_trigger_event(node)
        elif isinstance(node, Metadata):
            return self.eval_metadata(node)
        elif isinstance(node, FunctionDef):
            return self.eval_function_def(node)
        elif isinstance(node, Return):
            return self.eval_return(node)
        elif isinstance(node, Break):
            return self.eval_break(node)
        elif isinstance(node, Continue):
            return self.eval_continue(node)
        elif isinstance(node, Stop):
            return self.eval_stop(node)
        elif isinstance(node, FunctionCall):
            return self.eval_function_call(node)
        elif isinstance(node, CloneObject):
            return self.eval_clone_object(node)
        elif isinstance(node, DeleteObject):
            return self.eval_delete_object(node)
        elif isinstance(node, ResetObject):
            return self.eval_reset_object(node)
        elif isinstance(node, HideObject):
            return self.eval_hide_object(node)
        elif isinstance(node, ShowObject):
            return self.eval_show_object(node)
        elif isinstance(node, CountObjects):
            return self.eval_count_objects(node)
        elif isinstance(node, MoveObject):
            return self.eval_move_object(node)
        elif isinstance(node, PropertiesCommand):
            return self.eval_properties(node)
        elif isinstance(node, GotoRoom):
            return self.eval_goto(node)
        elif isinstance(node, LookCommand):
            return self.eval_look(node)
        elif isinstance(node, ConnectRooms):
            return self.eval_connect(node)
        elif isinstance(node, Help):
            return self.eval_help(node)
        else:
            raise RoshRuntimeError(f"Unknown statement type: {type(node).__name__}")

    def interpolate_string(self, string_value: str) -> str:
        """Handle string interpolation for {expression} patterns"""
        # Pattern to match {expression}
        pattern = r'\{([^}]+)\}'

        def replace_match(match):
            expr_str = match.group(1).strip()

            # Parse and evaluate the expression
            try:
                from .lexer import Lexer
                from .parser import Parser

                lexer = Lexer(expr_str)
                tokens = lexer.tokenize()
                parser = Parser(tokens)
                expr = parser.parse_expression()

                # Evaluate the expression
                value = self.eval_expression(expr)

                # Convert to string
                return str(rosh_to_python(value))
            except Exception as e:
                # If interpolation fails, keep the original {expression}
                return match.group(0)

        # Replace all {expression} with evaluated values
        return re.sub(pattern, replace_match, string_value)

    def eval_expression(self, node: ASTNode) -> Any:
        """Evaluate an expression and return its value"""
        if isinstance(node, Literal):
            # Handle string interpolation
            if isinstance(node.value, str) and '{' in node.value:
                return self.interpolate_string(node.value)
            return node.value

        elif isinstance(node, ListLiteral):
            # Evaluate all elements in the list
            return [self.eval_expression(elem) for elem in node.elements]

        elif isinstance(node, ListIndex):
            # Evaluate the list expression
            list_val = self.eval_expression(node.list_expr)

            if not isinstance(list_val, list):
                raise RoshTypeError(f"Cannot index non-list type: {type(list_val).__name__}")

            if node.is_slice:
                # Handle slicing: my_list[start:end]
                start = None
                end = None

                if node.start_expr:
                    start_val = self.eval_expression(node.start_expr)
                    if not isinstance(start_val, (int, float)):
                        raise RoshTypeError(f"Slice start must be a number, got {type(start_val).__name__}")
                    start = int(start_val)

                if node.end_expr:
                    end_val = self.eval_expression(node.end_expr)
                    if not isinstance(end_val, (int, float)):
                        raise RoshTypeError(f"Slice end must be a number, got {type(end_val).__name__}")
                    end = int(end_val)

                # Python-style slicing with None for omitted values
                return list_val[start:end]
            else:
                # Handle simple indexing: my_list[index]
                index_val = self.eval_expression(node.index_expr)
                if not isinstance(index_val, (int, float)):
                    raise RoshTypeError(f"List index must be a number, got {type(index_val).__name__}")

                index = int(index_val)
                # Use 0-based indexing
                if index < 0 or index >= len(list_val):
                    raise RoshRuntimeError(f"List index out of range: {index}")

                return list_val[index]

        elif isinstance(node, Random):
            return self.eval_random(node)

        elif isinstance(node, Length):
            return self.eval_length(node)

        elif isinstance(node, StringMethod):
            return self.eval_string_method(node)

        elif isinstance(node, Identifier):
            # Try to get the variable, but if it doesn't exist and looks like a simple name,
            # treat it as a string literal (for convenience)
            if self.current_env.exists(node.name):
                return self.current_env.get(node.name)
            else:
                # If it's a simple identifier (letters, numbers, dashes, underscores),
                # treat it as a string literal for convenience
                if node.name.replace('-', '').replace('_', '').isalnum():
                    return node.name
                else:
                    # Otherwise, it's an error
                    raise RoshNameError(f"Undefined variable: {node.name}")

        elif isinstance(node, PropertyAccess):
            return self.eval_property_access(node)

        elif isinstance(node, UnaryOp):
            return self.eval_unary_op(node)

        elif isinstance(node, BinaryOp):
            return self.eval_binary_op(node)

        elif isinstance(node, Comparison):
            return self.eval_comparison(node)

        elif isinstance(node, Contains):
            return self.eval_contains(node)

        elif isinstance(node, LogicalOp):
            return self.eval_logical_op(node)

        elif isinstance(node, FunctionCall):
            # Function calls can be used as expressions that return values
            return self.eval_function_call(node)

        else:
            raise RoshRuntimeError(f"Unknown expression type: {type(node).__name__}")

    def _create_typed_object(self, type_name: str) -> Optional[RoshObject]:
        """Helper to create a typed object programmatically.
        Returns the created object or None if creation failed.
        """
        # Create a synthetic CreateObject node
        node = CreateObject(name=type_name, body=[], parents=None, line=0)

        # Temporarily disable interactive feedback for bulk operations
        was_interactive = self.interactive
        self.interactive = False

        try:
            self.eval_create_object(node)
            # Get the created object (it was just defined in current_env)
            instances = self.instances.get(type_name, [])
            if instances:
                return instances[-1]  # Return the most recently created
            return None
        finally:
            self.interactive = was_interactive

    def eval_create_object(self, node: CreateObject) -> None:
        """Execute: create object <name> [from parent1, parent2] ... end"""
        # Block reserved object names
        if node.name == 'meta':
            raise RoshRuntimeError("Cannot create object 'meta': meta is a reserved implicit object")

        # Look up parent objects from environment
        parent_objects = []
        if node.parents:
            for parent_name in node.parents:
                parent = self.current_env.get(parent_name)
                if not isinstance(parent, RoshObject):
                    raise RoshTypeError(f"Parent '{parent_name}' is not an object")
                parent_objects.append(parent)

        # Determine if this is a template (first creation) or instance (subsequent)
        is_instance = self.current_env.exists(node.name)

        obj = RoshObject(name=node.name, parents=parent_objects)

        # If this is a simple "create <name>" with no body/parents,
        # check if it's a known object type and apply its properties
        if not node.body and not node.parents and not is_instance:
            from .data import get_known_objects_text
            known_objects = get_known_objects_text()
            if node.name in known_objects:
                obj.set('object_type', node.name)
                obj.set('description', known_objects[node.name])

        # Create a temporary environment for the object body
        # (so 'set name to "value"' works inside the object definition)
        old_env = self.current_env
        obj_env = Environment(parent=self.current_env)
        self.current_env = obj_env

        # Execute the body without recording undo entries (internal initialization)
        # We temporarily bind 'self' or the object name to the object
        obj_env.define(node.name, obj)

        with self.suspend_undo():
            for statement in node.body:
                if isinstance(statement, SetProperty):
                    # Handle 'set property to value' inside object
                    target = statement.target
                    value = self.eval_expression(statement.value)

                    if isinstance(target, Identifier):
                        # Simple property: set name to "Hero"
                        obj.set(target.name, value)
                    elif isinstance(target, PropertyAccess):
                        # Nested property: set position x to 0
                        self.eval_property_set(target, value, base_obj=obj)

        self.current_env = old_env

        # Register instance and determine final name
        if is_instance:
            # Instance creation: use auto-numbering from register_instance (ball-1, ball-2, etc.)
            self.register_instance(obj, type_name=node.name, explicit_name=None)
            final_name = obj.id  # register_instance sets obj.id to auto-numbered name
        else:
            # Template creation: use original name
            self.register_instance(obj, type_name=node.name, explicit_name=node.name)
            final_name = node.name

        self.current_env.define(final_name, obj)
        binding_env = self.current_env
        name = final_name
        binding_type = binding_env.bindings[name]['type']

        def undo_create():
            if name in binding_env.bindings:
                existing = binding_env.bindings[name]['value']
                if existing is obj:
                    self._detach_object_instance(obj)
                    del binding_env.bindings[name]

        def redo_create():
            binding_env.bindings[name] = {
                'value': obj,
                'type': binding_type
            }
            self._attach_object_instance(obj)

        self.push_undo(f"create {final_name}", undo_create, redo_create)

        # Provide feedback (only in interactive REPL mode)
        if self.interactive:
            if self.batch_mode:
                # Track for batch summary
                type_name = node.name
                self.batch_creates[type_name] = self.batch_creates.get(type_name, 0) + 1
            else:
                if final_name != node.name:
                    # Name was auto-numbered
                    self.color_out.success(f"Created '{final_name}' ('{node.name}' already exists)")
                else:
                    self.color_out.success(f"Created '{final_name}'")

    def eval_create_value(self, node: CreateValue) -> None:
        """Execute: create x to 5  OR  create x: number to 5"""
        from .environment import infer_type

        value = self.eval_expression(node.value)

        # If there's a type annotation, validate it
        if node.annotated_type is not None:
            inferred = infer_type(value)

            # Check if annotation matches inferred type
            if not self._types_match(node.annotated_type, inferred):
                ann_str = self._type_to_string(node.annotated_type)
                inf_str = self._type_to_string(inferred)
                raise RoshTypeError(
                    f"Type mismatch for variable '{node.name}': "
                    f"annotated as {ann_str}, but value is {inf_str}",
                    node.line
                )

        self.current_env.define(node.name, value)
        env = self.current_env
        value_snapshot = self._snapshot_value(value)
        value_type = env.bindings[node.name]['type']

        def undo_create_value():
            if node.name in env.bindings:
                del env.bindings[node.name]

        def redo_create_value():
            env.bindings[node.name] = {
                'value': self._snapshot_value(value_snapshot),
                'type': value_type
            }

        self.push_undo(f"create {node.name}", undo_create_value, redo_create_value)

    def _types_match(self, annotated, inferred):
        """Check if annotated type matches inferred type"""
        # Handle simple types
        if isinstance(annotated, str) and isinstance(inferred, str):
            return annotated == inferred

        # Handle list types
        if isinstance(annotated, tuple) and isinstance(inferred, tuple):
            if annotated[0] != 'list' or inferred[0] != 'list':
                return False

            ann_elem = annotated[1]
            inf_elem = inferred[1]

            # list<any> matches any list
            if ann_elem == 'any':
                return True

            # Empty list (list<any> inferred) matches any list annotation
            if inf_elem == 'any':
                return True

            return ann_elem == inf_elem

        # Mismatched categories
        return False

    def _type_to_string(self, type_spec):
        """Convert a type specification to a readable string"""
        if isinstance(type_spec, str):
            return type_spec
        elif isinstance(type_spec, tuple):
            return f"{type_spec[0]}<{type_spec[1]}>"
        else:
            return str(type_spec)

    def eval_set_property(self, node: SetProperty) -> None:
        """Execute: set <target> to <value>"""
        value = self.eval_expression(node.value)
        target = node.target

        if isinstance(target, Identifier):
            name = target.name
            # Check if we have a current object context (set via 'get')
            if self.current_object is not None:
                # Set property on current object
                prev_stack = self._snapshot_property_stack(self.current_object, name)
                self.current_object.set(name, value)
                new_stack = self._snapshot_property_stack(self.current_object, name)

                def undo_prop():
                    self._restore_property_stack(self.current_object, name, prev_stack)

                def redo_prop():
                    self._restore_property_stack(self.current_object, name, new_stack)

                self.push_undo(f"{self.current_object_name}.{name}", undo_prop, redo_prop)
                if self.interactive:
                    self.color_out.success(f"{self.current_object_name}.{name} = {value}")
            elif self.current_env.exists(target.name):
                # Setting an existing variable
                binding_env = self._find_env_for_binding(name) or self.current_env
                prev_value = self._snapshot_value(binding_env.bindings[name]['value'])
                self.current_env.set(name, value)
                new_value = self._snapshot_value(value)

                def undo_assign(env=binding_env, var=name, previous=prev_value):
                    if var in env.bindings:
                        env.bindings[var]['value'] = self._snapshot_value(previous)

                def redo_assign(env=binding_env, var=name, nxt=new_value):
                    if var in env.bindings:
                        env.bindings[var]['value'] = self._snapshot_value(nxt)

                self.push_undo(f"set {name}", undo_assign, redo_assign)
                if self.interactive:
                    self.color_out.success(f"{name} = {repr(value) if isinstance(value, str) else value}")
            else:
                # Define a new variable
                self.current_env.define(name, value)
                binding_env = self.current_env
                value_snapshot = self._snapshot_value(value)
                value_type = binding_env.bindings[name]['type']

                def undo_define(env=binding_env, var=name):
                    if var in env.bindings:
                        del env.bindings[var]

                def redo_define(env=binding_env, var=name, val=value_snapshot, typ=value_type):
                    env.bindings[var] = {
                        'value': self._snapshot_value(val),
                        'type': typ
                    }

                self.push_undo(f"define {name}", undo_define, redo_define)
                if self.interactive:
                    self.color_out.success(f"{name} = {repr(value) if isinstance(value, str) else value}")

        elif isinstance(target, ListIndex):
            # Setting a list element
            if target.is_slice:
                raise RoshRuntimeError("Cannot assign to a list slice (slices are read-only)")

            list_val = self.eval_expression(target.list_expr)
            index_val = self.eval_expression(target.index_expr)

            if not isinstance(list_val, list):
                raise RoshTypeError(f"Cannot index non-list type: {type(list_val).__name__}")
            if not isinstance(index_val, (int, float)):
                raise RoshTypeError(f"List index must be a number, got {type(index_val).__name__}")

            index = int(index_val)
            if index < 0 or index >= len(list_val):
                raise RoshRuntimeError(f"List index out of range: {index}")

            prev_value = self._snapshot_value(list_val[index])
            list_val[index] = value
            new_value = self._snapshot_value(value)

            desc = "list"
            if isinstance(target.list_expr, Identifier):
                desc = target.list_expr.name

            def undo_list_assignment(lst=list_val, idx=index, prev=prev_value):
                lst[idx] = self._snapshot_value(prev)

            def redo_list_assignment(lst=list_val, idx=index, nxt=new_value):
                lst[idx] = self._snapshot_value(nxt)

            self.push_undo(f"{desc}[{index}]", undo_list_assignment, redo_list_assignment)

        elif isinstance(target, PropertyAccess):
            # Setting an object property
            self.eval_property_set(target, value)

    def eval_set_all(self, node: SetAll) -> None:
        """Execute: set all <type> <property> to <value> - Stage bulk operation"""
        type_name = node.type_name
        prop_name = node.property_name
        value = self.eval_expression(node.value)

        # Find matching type (with plural handling)
        actual_type = self._find_type_with_plural(type_name)
        if actual_type is None:
            raise RoshRuntimeError(f"No instances of type '{type_name}' found")

        # Get all instances of this type
        instances = self.instances.get(actual_type, [])
        if not instances:
            raise RoshRuntimeError(f"No instances of type '{actual_type}' found")

        # Stage the operation - don't execute yet
        self.pending_operation = {
            'type': 'set_all',
            'targets': instances,
            'type_name': actual_type,
            'prop': prop_name,
            'value': value
        }

        # Show confirmation prompt
        self.color_out.warning(f"set {prop_name} to {repr(value) if isinstance(value, str) else value} on {len(instances)} {actual_type}(s)")
        self.color_out.info("Type 'yes' or 'go' to execute")

    def eval_confirm(self, node: Confirm) -> None:
        """Execute: confirm | yes | go - Execute pending bulk operation"""
        if self.pending_operation is None:
            self.color_out.warning("No pending operation to confirm")
            return

        op = self.pending_operation
        self.pending_operation = None  # Clear before executing

        # Start new undo group so entire bulk operation can be undone together
        self.start_undo_group()

        if op['type'] == 'set_all':
            targets = op['targets']
            prop_name = op['prop']
            value = op['value']
            count = 0

            for obj in targets:
                if isinstance(obj, RoshObject):
                    obj.set(prop_name, value)
                    count += 1

            self.color_out.success(f"Set {prop_name} = {repr(value) if isinstance(value, str) else value} on {count} object(s)")

        elif op['type'] == 'bulk_create':
            count = op['count']
            type_name = op['type_name']
            modifiers = op['modifiers']

            # Known color and size mappings
            known_colors = {'red', 'green', 'blue', 'yellow', 'cyan', 'magenta',
                            'white', 'black', 'orange', 'purple', 'pink', 'gray',
                            'grey', 'gold', 'silver'}
            known_sizes = {'big': 2, 'large': 2, 'huge': 3, 'small': 0.5, 'tiny': 0.25}

            # Collect unknown modifiers for description
            description_words = []
            for mod in modifiers:
                if mod not in known_colors and mod not in known_sizes:
                    description_words.append(mod)

            # Build description: "angry orc", "big angry orc", etc.
            description = ' '.join(description_words + [type_name]) if description_words else None

            self.batch_mode = True
            created = 0
            for i in range(count):
                # Create the object
                obj = self._create_typed_object(type_name)
                if obj:
                    # Apply known modifiers
                    for mod in modifiers:
                        if mod in known_colors:
                            obj.set('color', mod)
                        elif mod in known_sizes:
                            obj.set('scale', known_sizes[mod])
                    # Set description if we have unknown modifiers
                    if description:
                        obj.set('description', description)
                    created += 1
            self.batch_mode = False
            self.color_out.success(f"Created {created} {type_name}(s)")

        elif op['type'] == 'bulk_delete':
            targets = op['targets']
            count = 0
            for obj in targets:
                # RoshObject uses .id (display ID like "ball-1") or .name
                if isinstance(obj, RoshObject):
                    name = obj.id or obj.name
                else:
                    name = obj.get('_id') or obj.get('_name') if hasattr(obj, 'get') else None
                if name and self.current_env.exists(name):
                    # Find the right environment
                    env = self._find_env_for_binding(name) or self.current_env
                    if name in env.bindings:
                        # Clean up instance tracking
                        if isinstance(obj, RoshObject):
                            self._detach_object_instance(obj)
                        del env.bindings[name]
                        count += 1
            self.color_out.success(f"Deleted {count} object(s)")

        elif op['type'] == 'bulk_get':
            targets = op['targets']
            # Push all targets onto the data stack
            for obj in targets:
                self.data_stack.append(obj)
            self.color_out.success(f"Selected {len(targets)} object(s)")

        elif op['type'] == 'bulk_set':
            targets = op['targets']
            prop_name = op['prop']
            value = op['value']
            count = 0
            for obj in targets:
                if isinstance(obj, RoshObject):
                    obj.set(prop_name, value)
                    count += 1
            self.color_out.success(f"Set {prop_name} on {count} object(s)")

    def eval_repeat(self, node: Repeat) -> None:
        """Execute: repeat - Re-execute last substantive command"""
        if self.last_command is None:
            self.color_out.warning("No command to repeat")
            return

        # Re-execute the last command
        self.color_out.info("Repeating...")
        self.eval_statement(self.last_command)

    def eval_bulk_operation(self, node: BulkOperation) -> None:
        """Stage bulk operation for confirmation"""
        operation = node.operation
        count = node.count
        type_name = node.type_name
        modifiers = node.modifiers
        auto_confirm = node.auto_confirm

        # Threshold for requiring confirmation (can be configured later)
        confirm_threshold = 10

        if operation == 'create':
            # Auto-confirm (trailing 'go') or small count: execute immediately
            if auto_confirm or count < confirm_threshold:
                self.pending_operation = {
                    'type': 'bulk_create',
                    'count': count,
                    'type_name': type_name,
                    'modifiers': modifiers
                }
                self.eval_confirm(Confirm(line=node.line))
            else:
                # Large count without auto-confirm: ask for confirmation
                self.pending_operation = {
                    'type': 'bulk_create',
                    'count': count,
                    'type_name': type_name,
                    'modifiers': modifiers
                }
                self.color_out.warning(f"Create {count} {type_name}(s)?")
                self.color_out.info("Type 'yes' or 'go' to execute")

        elif operation == 'delete':
            instances = self.instances.get(type_name, [])
            if not instances:
                self.color_out.warning(f"No {type_name} objects found")
                return

            targets = instances[:count]
            self.pending_operation = {
                'type': 'bulk_delete',
                'targets': targets,
                'type_name': type_name
            }
            # Auto-confirm (trailing 'go') or small count: execute immediately
            if auto_confirm or len(targets) < confirm_threshold:
                self.eval_confirm(Confirm(line=node.line))
            else:
                self.color_out.warning(f"Delete {len(targets)} {type_name}(s)?")
                self.color_out.info("Type 'yes' or 'go' to execute")

        elif operation == 'get':
            instances = self.instances.get(type_name, [])
            if not instances:
                self.color_out.warning(f"No {type_name} objects found")
                return

            targets = instances[:count]
            # Get doesn't need confirmation - it's read-only
            for obj in targets:
                self.data_stack.append(obj)
            self.color_out.success(f"Selected {len(targets)} {type_name}(s)")

        elif operation == 'set':
            instances = self.instances.get(type_name, [])
            if not instances:
                self.color_out.warning(f"No {type_name} objects found")
                return

            targets = instances[:count]
            value = self.eval_expression(node.property_value)

            if len(targets) >= confirm_threshold:
                self.pending_operation = {
                    'type': 'bulk_set',
                    'targets': targets,
                    'prop': node.property_name,
                    'value': value,
                    'type_name': type_name
                }
                self.color_out.warning(f"Set {node.property_name} on {len(targets)} {type_name}(s)?")
                self.color_out.info("Type 'yes' or 'go' to execute")
            else:
                self.pending_operation = {
                    'type': 'bulk_set',
                    'targets': targets,
                    'prop': node.property_name,
                    'value': value,
                    'type_name': type_name
                }
                self.eval_confirm(Confirm(line=node.line))

    def eval_append(self, node) -> None:
        """Execute: append <item> to <list>"""
        item = self.eval_expression(node.item)
        target = node.target

        if isinstance(target, Identifier):
            # Get the list
            if not self.current_env.exists(target.name):
                raise RoshNameError(f"Undefined variable: {target.name}")

            list_val = self.current_env.get(target.name)
            if not isinstance(list_val, list):
                raise RoshTypeError(f"Cannot append to non-list type: {type(list_val).__name__}")

            list_val.append(item)

        elif isinstance(target, PropertyAccess):
            # Get the list from object property
            obj_val = self.eval_property_access(target)
            if not isinstance(obj_val, list):
                raise RoshTypeError(f"Cannot append to non-list type: {type(obj_val).__name__}")

            obj_val.append(item)

        else:
            raise RoshTypeError(f"Cannot append to: {type(target).__name__}")

    def eval_remove(self, node) -> None:
        """Execute: remove <item> from <list>"""
        item = self.eval_expression(node.item)
        target = node.target

        if isinstance(target, Identifier):
            # Get the list
            if not self.current_env.exists(target.name):
                raise RoshNameError(f"Undefined variable: {target.name}")

            list_val = self.current_env.get(target.name)
            if not isinstance(list_val, list):
                raise RoshTypeError(f"Cannot remove from non-list type: {type(list_val).__name__}")

            # Remove the first occurrence of the item
            if item in list_val:
                list_val.remove(item)
            else:
                raise RoshRuntimeError(f"Item not found in list: {item}")

        elif isinstance(target, PropertyAccess):
            # Get the list from object property
            obj_val = self.eval_property_access(target)
            if not isinstance(obj_val, list):
                raise RoshTypeError(f"Cannot remove from non-list type: {type(obj_val).__name__}")

            # Remove the first occurrence of the item
            if item in obj_val:
                obj_val.remove(item)
            else:
                raise RoshRuntimeError(f"Item not found in list: {item}")

        else:
            raise RoshTypeError(f"Cannot remove from: {type(target).__name__}")

    def eval_increment(self, node) -> None:
        """Execute: increment <variable>"""
        target = node.target

        if isinstance(target, Identifier):
            # Increment simple variable
            if not self.current_env.exists(target.name):
                raise RoshNameError(f"Undefined variable: {target.name}")

            current_val = self.current_env.get(target.name)
            if not isinstance(current_val, (int, float)):
                raise RoshTypeError(f"Cannot increment non-numeric type: {type(current_val).__name__}")

            self.current_env.set(target.name, current_val + 1)

        elif isinstance(target, PropertyAccess):
            # Increment object property
            obj_value = self.eval_expression(target.object)
            if not isinstance(obj_value, RoshObject):
                raise RoshTypeError(f"Cannot access property of non-object")

            current_val = obj_value.get(target.property)
            if not isinstance(current_val, (int, float)):
                raise RoshTypeError(f"Cannot increment non-numeric type: {type(current_val).__name__}")

            obj_value.set(target.property, current_val + 1)

        else:
            raise RoshTypeError(f"Cannot increment: {type(target).__name__}")

    def eval_decrement(self, node) -> None:
        """Execute: decrement <variable>"""
        target = node.target

        if isinstance(target, Identifier):
            # Decrement simple variable
            if not self.current_env.exists(target.name):
                raise RoshNameError(f"Undefined variable: {target.name}")

            current_val = self.current_env.get(target.name)
            if not isinstance(current_val, (int, float)):
                raise RoshTypeError(f"Cannot decrement non-numeric type: {type(current_val).__name__}")

            self.current_env.set(target.name, current_val - 1)

        elif isinstance(target, PropertyAccess):
            # Decrement object property
            obj_value = self.eval_expression(target.object)
            if not isinstance(obj_value, RoshObject):
                raise RoshTypeError(f"Cannot access property of non-object")

            current_val = obj_value.get(target.property)
            if not isinstance(current_val, (int, float)):
                raise RoshTypeError(f"Cannot decrement non-numeric type: {type(current_val).__name__}")

            obj_value.set(target.property, current_val - 1)

        else:
            raise RoshTypeError(f"Cannot decrement: {type(target).__name__}")

    def eval_push_property(self, node: PushProperty) -> None:
        """Execute: push <target> <value>"""
        value = self.eval_expression(node.value)
        target = node.target

        if isinstance(target, Identifier):
            # Pushing to a simple variable not supported - must be object property
            raise RoshTypeError(f"Cannot push to variable '{target.name}' - push only works on object properties")

        elif isinstance(target, PropertyAccess):
            # Push to object property
            obj_value = self.eval_expression(target.object)
            if not isinstance(obj_value, RoshObject):
                raise RoshTypeError(f"Cannot push property of non-object")
            obj_value.push(target.property, value)

    def eval_pop_property(self, node: PopProperty) -> None:
        """Execute: pop <target>"""
        target = node.target

        if isinstance(target, Identifier):
            # Popping from a simple variable not supported - must be object property
            raise RoshTypeError(f"Cannot pop from variable '{target.name}' - pop only works on object properties")

        elif isinstance(target, PropertyAccess):
            # Pop from object property
            obj_value = self.eval_expression(target.object)
            if not isinstance(obj_value, RoshObject):
                raise RoshTypeError(f"Cannot pop property of non-object")
            obj_value.pop(target.property)

    def eval_stack_command(self, node: StackCommand) -> None:
        """Execute: stack - Display the data stack contents"""
        if not self.data_stack:
            print("Stack is empty", file=self.output_stream)
        else:
            print(f"Stack ({len(self.data_stack)} items):", file=self.output_stream)
            for i, value in enumerate(reversed(self.data_stack)):
                output = rosh_to_python(value)
                print(f"  [{len(self.data_stack) - i - 1}] {output}", file=self.output_stream)

    def eval_property_access(self, node: PropertyAccess) -> Any:
        """Evaluate: obj.property or obj.prop1.prop2"""
        obj_value = self.eval_expression(node.object)

        if not isinstance(obj_value, RoshObject):
            raise RoshTypeError(f"Cannot access property of non-object: {type(obj_value).__name__}")

        return obj_value.get(node.property)

    def _is_meta_path(self, node) -> bool:
        """Check if this property access path starts from the meta object"""
        if isinstance(node, Identifier):
            return node.name == 'meta'
        elif isinstance(node, PropertyAccess):
            return self._is_meta_path(node.object)
        return False

    def _get_or_create_nested(self, node: PropertyAccess) -> RoshObject:
        """Get a nested property, auto-creating intermediate objects for meta paths.

        For meta objects, this enables: set meta.game.title to "X"
        where meta.game is auto-created as a RoshObject if it doesn't exist.
        """
        is_meta = self._is_meta_path(node)

        if isinstance(node.object, Identifier):
            obj_value = self.current_env.get(node.object.name)
        elif isinstance(node.object, PropertyAccess):
            obj_value = self._get_or_create_nested(node.object)
        else:
            raise RoshRuntimeError(f"Cannot set property on: {type(node.object).__name__}")

        if not isinstance(obj_value, RoshObject):
            raise RoshTypeError(f"Cannot set property of non-object: {type(obj_value).__name__}")

        # Check if property exists
        prop_value = obj_value.get(node.property)

        # Auto-create nested objects for meta paths
        if prop_value is None and is_meta:
            nested_obj = RoshObject(name=node.property)
            nested_obj._is_meta = True  # Mark as part of meta tree
            obj_value.set(node.property, nested_obj)
            return nested_obj
        elif prop_value is None:
            raise RoshTypeError(f"Cannot set property of non-object: NoneType")

        if not isinstance(prop_value, RoshObject):
            raise RoshTypeError(f"Cannot set property of non-object: {type(prop_value).__name__}")

        return prop_value

    def eval_property_set(self, node: PropertyAccess, value: Any, base_obj: RoshObject = None) -> None:
        """Set a property: obj.property = value or obj.prop1.prop2 = value

        For meta objects, auto-creates intermediate objects:
            set meta.game.title to "X" creates meta.game if needed
        """
        if base_obj is None:
            # Get the base object from the environment
            if isinstance(node.object, Identifier):
                obj_value = self.current_env.get(node.object.name)
            elif isinstance(node.object, PropertyAccess):
                # Use special handling for meta paths (auto-create intermediates)
                obj_value = self._get_or_create_nested(node.object)
            else:
                raise RoshRuntimeError(f"Cannot set property on: {type(node.object).__name__}")
        else:
            # Base object provided (for object initialization)
            if isinstance(node.object, Identifier):
                # This is the base object
                obj_value = base_obj
            elif isinstance(node.object, PropertyAccess):
                obj_value = self._get_or_create_nested(node.object)
            else:
                raise RoshRuntimeError(f"Cannot set property on: {type(node.object).__name__}")

        if not isinstance(obj_value, RoshObject):
            raise RoshTypeError(f"Cannot set property of non-object: {type(obj_value).__name__}")

        prev_stack = self._snapshot_property_stack(obj_value, node.property)
        obj_value.set(node.property, value)
        new_stack = self._snapshot_property_stack(obj_value, node.property)

        desc = self._describe_property_path(node) if base_obj is None else f"{base_obj.name}.{node.property}"

        def undo_prop():
            self._restore_property_stack(obj_value, node.property, prev_stack)

        def redo_prop():
            self._restore_property_stack(obj_value, node.property, new_stack)

        self.push_undo(desc, undo_prop, redo_prop)

        # Provide feedback (only in interactive mode and not during object initialization)
        if self.interactive and base_obj is None:
            self.color_out.success(f"{desc} = {repr(value) if isinstance(value, str) else value}")

    def eval_print(self, node: Print) -> None:
        """Execute: print <expression>

        Special handling for bare identifiers:
        - If identifier exists as variable/object, print its value
        - If not, treat the identifier name as a bare string
        """
        # Special case: bare identifier that might not exist
        if isinstance(node.expression, Identifier):
            name = node.expression.name
            if self.current_env.exists(name):
                # It's a variable - print its value
                value = self.eval_expression(node.expression)
                output = rosh_to_python(value)
            else:
                # Not a variable - print the name as a bare string
                output = name
        else:
            # Normal expression evaluation
            value = self.eval_expression(node.expression)
            output = rosh_to_python(value)

        if isinstance(output, str):
            print(output, file=self.output_stream)
        else:
            print(output, file=self.output_stream)

    def eval_print_stack(self, node) -> None:
        """Execute: print stack - pops from stack and prints"""
        if not self.data_stack:
            raise RoshRuntimeError("Cannot print stack: stack is empty")
        value = self.data_stack.pop()
        output = rosh_to_python(value)

        if isinstance(output, str):
            print(output, file=self.output_stream)
        else:
            print(output, file=self.output_stream)

    def eval_input(self, node: Input) -> None:
        """Execute: input <variable_name> [prompt <string>] - reads line from stdin and stores in variable

        In test mode, reads from test_inputs instead of stdin.
        """
        if self.test_mode:
            # Test mode: use mocked input
            if self.test_input_index >= len(self.test_inputs):
                raise RoshRuntimeError(
                    f"Test mode: No more test inputs available "
                    f"(needed input for '{node.variable_name}')"
                )
            user_input = self.test_inputs[self.test_input_index]
            self.test_input_index += 1
            # Log to stderr (not stdout, to keep output clean for testing)
            sys.stderr.write(f"[TEST INPUT: {user_input}]\n")
            # Define the variable
            self.current_env.define(node.variable_name, user_input)
        else:
            # Normal mode: read from stdin
            try:
                # Read a line from stdin with optional prompt
                if node.prompt:
                    user_input = input(node.prompt)
                else:
                    user_input = input()
                # Define the variable (creates it if it doesn't exist)
                self.current_env.define(node.variable_name, user_input)
            except EOFError:
                # Handle EOF gracefully (e.g., when input is piped)
                self.current_env.define(node.variable_name, "")

    def eval_get(self, node: Get) -> None:
        """Execute: get <target> - pushes value onto stack

        Supports:
        - get ball        → gets ball variable (or first instance if many)
        - get ball 5      → gets instance #5
        - get all ball    → gets all instances as list
        """
        target = node.target

        if isinstance(target, Identifier):
            # Check if this is an instance reference
            if node.get_all:
                # Get all instances of this type
                instances = self.get_instance(target.name, index=None)
                if instances is None or len(instances) == 0:
                    raise RoshRuntimeError(f"No instances of type '{target.name}' found")

                # Push all instances onto stack
                for inst in instances:
                    self.data_stack.append(inst)
                self.color_out.info(f"Got {len(instances)} instance(s) of {target.name}")

            elif node.instance_index is not None:
                # Get specific instance by index
                instance = self.get_instance(target.name, index=node.instance_index)
                if instance is None:
                    raise RoshRuntimeError(f"Instance #{node.instance_index} of type '{target.name}' not found")

                self.data_stack.append(instance)
                # Show feedback
                instances = self.instances.get(target.name, [])
                self.color_out.info(f"Got {instance.id} ({node.instance_index} of {len(instances)})")

            else:
                # Get simple variable
                value = self.current_env.get(target.name)
                self.data_stack.append(value)

                # Set as current object for contextual commands
                if isinstance(value, RoshObject):
                    self.current_object = value
                    self.current_object_name = target.name

                # Show feedback if this is an instance of a type with multiple instances
                if isinstance(value, RoshObject) and value.id:
                    # Extract type from ID (e.g., "ball-1" → "ball")
                    type_name = value.id.rsplit('-', 1)[0] if '-' in value.id else value.name
                    instances = self.instances.get(type_name, [])
                    if len(instances) > 1:
                        # Find which instance this is
                        instance_num = 1
                        for i, inst in enumerate(instances, 1):
                            if inst.uuid == value.uuid:
                                instance_num = i
                                break
                        self.color_out.info(f"Got {value.id} ({instance_num} of {len(instances)})")

        elif isinstance(target, PropertyAccess):
            # Get property from object
            value = self.eval_property_access(target)
            self.data_stack.append(value)
        elif isinstance(target, ListIndex):
            # Get list element
            value = self.eval_expression(target)
            self.data_stack.append(value)
        else:
            raise RoshRuntimeError(f"Cannot get value from: {type(target).__name__}")

    def eval_dump(self, node: Dump) -> None:
        """Execute: dump [target] - outputs state or specific object as JSON"""
        import json
        from .values import rosh_to_python

        if node.target:
            # Dump specific object
            if self.current_env.exists(node.target):
                obj = self.current_env.get(node.target)
                obj_data = rosh_to_python(obj)
                json_output = json.dumps(obj_data, indent=2)
            else:
                raise RoshRuntimeError(f"Object '{node.target}' not found")
        else:
            # Dump entire state
            state = self.get_state()
            json_output = json.dumps(state, indent=2)

        print(json_output, file=self.output_stream)

    def eval_save(self, node: Save) -> None:
        """Execute: save [as toon|json] [filepath] - saves state to file

        Supports multiple formats:
        - json: JSON format (default, human-readable)
        - toon: TOON format (Token-Oriented Object Notation, LLM-optimized)

        Format can be specified with 'as toon' or 'as json', or inferred from extension.
        """
        import json

        # Determine format (explicit > extension > default)
        format_type = node.format  # May be 'toon', 'json', or None

        # Determine filepath
        if node.filepath:
            filepath_value = self.eval_expression(node.filepath)
            filepath = rosh_to_python(filepath_value)
            if not isinstance(filepath, str):
                raise RoshTypeError(f"save requires a string filepath, got {type(filepath).__name__}")
            # Infer format from extension if not explicitly specified
            if format_type is None:
                if filepath.endswith('.toon'):
                    format_type = 'toon'
                else:
                    format_type = 'json'
        else:
            # Default filename based on format
            if format_type == 'toon':
                filepath = "rosh-state.toon"
            else:
                filepath = "rosh-state.json"
                format_type = 'json'

        # Get state
        state = self.get_state()

        # Save in appropriate format
        try:
            if format_type == 'toon':
                # Save as TOON format
                from .toon_encoder import save_as_toon
                save_as_toon(filepath, state)
                self.color_out.success(f"State saved to {filepath} (TOON format)")
            else:
                # Default to JSON format
                with open(filepath, 'w') as f:
                    json.dump(state, f, indent=2)
                self.color_out.success(f"State saved to {filepath}")
        except IOError as e:
            raise RoshRuntimeError(f"Failed to save state to {filepath}: {e}")

    def eval_load(self, node: Load) -> None:
        """Execute: load [filepath] - restores state from file

        Supports:
        - .json: JSON format (default)
        - .toon: TOON format (Token-Oriented Object Notation)

        If no filepath provided, defaults to rosh-state.json
        """
        import json
        from .values import RoshObject

        # Default filepath if none provided
        if node.filepath is None:
            filepath = "rosh-state.json"
        else:
            # Evaluate the filepath expression to get the path string
            filepath_value = self.eval_expression(node.filepath)
            filepath = rosh_to_python(filepath_value)

            if not isinstance(filepath, str):
                raise RoshTypeError(f"load requires a string filepath, got {type(filepath).__name__}")

        # Load based on file extension
        try:
            if filepath.endswith('.toon'):
                from .toon_decoder import load_from_toon, TOONDecodeError
                try:
                    state = load_from_toon(filepath)
                except TOONDecodeError as e:
                    raise RoshRuntimeError(f"Invalid TOON format in file {filepath}: {e}")
            else:
                # Default to JSON
                with open(filepath, 'r') as f:
                    state = json.load(f)
        except FileNotFoundError:
            raise RoshRuntimeError(f"File not found: {filepath}")
        except json.JSONDecodeError as e:
            raise RoshRuntimeError(f"Invalid JSON in file {filepath}: {e}")

        # Clear current state
        self.global_env.bindings.clear()
        self.data_stack.clear()

        # Clear instance tracking
        if hasattr(self, 'instances'):
            self.instances.clear()
        if hasattr(self, 'uuid_map'):
            self.uuid_map.clear()
        if hasattr(self, 'instance_counters'):
            self.instance_counters.clear()

        # Restore instance counters (v0.0.4+)
        if "instance_counters" in state:
            if not hasattr(self, 'instance_counters'):
                self.instance_counters = {}
            self.instance_counters.update(state["instance_counters"])

        # Restore variables
        if "variables" in state:
            for name, value in state["variables"].items():
                # Deserialize the value
                deserialized = self._deserialize_value(value)

                # Skip None values (from failed function deserialization)
                if deserialized is None:
                    continue

                self.global_env.define(name, deserialized)

                # Rebuild instance tracking for RoshObjects (v0.0.4+)
                if isinstance(deserialized, RoshObject):
                    # Ensure tracking structures exist
                    if not hasattr(self, 'instances'):
                        self.instances = {}
                    if not hasattr(self, 'uuid_map'):
                        self.uuid_map = {}

                    # Add to uuid_map
                    self.uuid_map[deserialized.uuid] = deserialized

                    # Determine type name from ID
                    if deserialized.id:
                        type_name = deserialized.id.rsplit('-', 1)[0] if '-' in deserialized.id else deserialized.name
                    else:
                        type_name = deserialized.name

                    # Add to instances list
                    if type_name not in self.instances:
                        self.instances[type_name] = []
                    self.instances[type_name].append(deserialized)

        # Restore stack
        if "stack" in state:
            for value in state["stack"]:
                deserialized = self._deserialize_value(value)
                self.data_stack.append(deserialized)

        # Success message
        if hasattr(self, 'color_out') and self.color_out:
            self.color_out.success(f"State loaded from {filepath}")

    def eval_prompt(self, node: Prompt) -> None:
        """Execute: prompt [exec] <message> [using <vars>] [into <target>]"""
        # Evaluate the message expression
        message_value = self.eval_expression(node.message)
        message = rosh_to_python(message_value)

        if not isinstance(message, str):
            raise RoshTypeError(f"prompt message must be a string, got {type(message).__name__}")

        # Build context from specified variables
        context = {}
        if node.context_vars:
            for var_name in node.context_vars:
                try:
                    value = self.global_env.get(var_name)
                    # Convert to JSON-serializable format
                    if isinstance(value, RoshObject):
                        context[var_name] = value.to_json()
                    else:
                        context[var_name] = rosh_to_python(value)
                except:
                    # Variable not found - skip it
                    pass

        # Get AI configuration
        config = get_config()
        provider_name = config.get('ai.provider', 'openai')
        api_key = config.get_ai_key(provider_name)

        if not api_key:
            # Provide helpful setup instructions
            setup_msg = f"""
╭─────────────────────────────────────────────────────────╮
│  No API key found for AI provider '{provider_name}'    │
╰─────────────────────────────────────────────────────────╯

Quick setup (choose one):

1. Environment Variable (recommended):
   export OPENAI_API_KEY="sk-your-key-here"

   Add to ~/.bashrc or ~/.zshrc to make permanent

2. Config File:
   mkdir -p ~/.rosh
   cat > ~/.rosh/config.json << 'EOF'
   {{
     "ai": {{
       "provider": "openai",
       "model": "gpt-4o-mini",
       "openai_api_key": "sk-your-key-here"
     }}
   }}
   EOF

3. Get API Key:
   OpenAI: https://platform.openai.com/api-keys
   Anthropic: https://console.anthropic.com/

Then try again! See AI_SETUP.md for full guide.
"""
            raise RoshRuntimeError(setup_msg)

        # Get model and create provider
        model = config.get('ai.model')
        try:
            provider = get_provider(provider_name, api_key, model)
        except Exception as e:
            raise RoshRuntimeError(f"Failed to initialize AI provider: {e}")

        # Add Rosh context to prompt
        rosh_system_context = """You are helping a user with Rosh, a programming language for creating games and simulations.

Rosh is an English-like language where code sounds like talking to a person. Key features:
- create object <name> ... end - creates game objects with properties
- set <property> to <value> - sets properties on objects
- Transpiles to Phaser (browser), Pygame (desktop), Three.js (3D), and Unity

IMPORTANT: Rosh uses spaces, NOT commas. No punctuation in values.

Example Rosh code:
```rosh
create object ball
    set color to "blue"
    set radius to 2
    set x to 100
    set y to 200
end
```

"""

        # Enhance prompt for code generation in exec mode
        if node.exec_mode:
            code_gen_prompt = f"""{rosh_system_context}Generate ONLY valid Rosh code, no explanations or markdown.

User request: {message}

Generate executable Rosh code (no markdown fences):"""
            message = code_gen_prompt
        else:
            # For regular prompts, still add Rosh context
            message = f"""{rosh_system_context}User asks: {message}

If they're asking about creating something in a game, respond with Rosh code examples. Be concise and helpful."""

        # Make the prompt call
        try:
            response = provider.prompt(message, context)
        except Exception as e:
            raise RoshRuntimeError(f"AI prompt failed: {e}")

        # Handle response based on mode
        if node.exec_mode:
            # Show generated code
            print(f"🤖 AI generated code:\n")
            print("─" * 60)
            print(response)
            print("─" * 60)
            print()

            # SECURITY: Require user confirmation before executing AI code
            confirm = input("Execute this AI-generated code? [y/N]: ").strip().lower()
            if confirm not in ('y', 'yes'):
                print("❌ Execution cancelled")
                # Store the code in target variable if specified, so user can review/execute later
                if node.target:
                    self.global_env.define(node.target, response)
                    print(f"💾 Code saved to '{node.target}' (use 'eval {node.target}' to execute)")
                return

            # Execute the generated code
            # ⚠️ DANGER: AI-generated code runs with FULL USER PERMISSIONS
            # TODO: Implement sandboxing before multi-user support
            #   - NO filesystem access without explicit permission
            #   - NO network access without explicit permission
            #   - Resource limits (CPU, memory, time)
            #   - See Milestone 9 in PROJECT-PLAN.md
            # For now: User confirmation is the ONLY safety check
            print(f"▶️  Executing...\n")
            try:
                self._execute_code_string(response)
                print(f"\n✓ Execution complete")
            except Exception as e:
                raise RoshRuntimeError(f"Failed to execute AI-generated code: {e}")
        else:
            # Store or print result
            if node.target:
                self.global_env.define(node.target, response)
            else:
                print(response)

    def eval_eval(self, node: Eval) -> None:
        """Execute: eval <code_string> - Execute Rosh code from a string"""
        # Evaluate the code expression to get the code string
        code_value = self.eval_expression(node.code_expr)
        code = rosh_to_python(code_value)

        if not isinstance(code, str):
            raise RoshTypeError(f"eval requires a string, got {type(code).__name__}")

        # Execute the code
        # NOTE: eval is safe for single-user, local development
        # The user controls what code is evaluated - no different than typing it in REPL
        # TODO: For multi-user (Milestone 9), eval will require sandboxing
        # See docs/EVAL-SAFETY.md for rationale
        self._execute_code_string(code)

    def _execute_code_string(self, code: str) -> None:
        """Helper: Parse and execute a string of Rosh code"""
        from .lexer import Lexer
        from .parser import Parser

        # Strip markdown code fences if present (AI often adds these)
        code = code.strip()
        if code.startswith('```'):
            lines = code.split('\n')
            # Remove first line (```rosh or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            code = '\n'.join(lines)

        try:
            # Lex the code
            lexer = Lexer(code)
            tokens = lexer.tokenize()

            # Parse the code
            parser = Parser(tokens)
            program = parser.parse()

            # Execute in current environment (not a fresh one!)
            for statement in program.statements:
                self.eval_statement(statement)

        except Exception as e:
            raise RoshRuntimeError(f"Error executing code: {e}")

    def eval_read(self, node: Read) -> None:
        """Execute: read [json] <filepath> into <target>"""
        # Evaluate filepath
        filepath_value = self.eval_expression(node.filepath)
        filepath = rosh_to_python(filepath_value)

        if not isinstance(filepath, str):
            raise RoshTypeError(f"read requires a string filepath, got {type(filepath).__name__}")

        # TODO: For multi-user, implement filesystem restrictions
        #   - Allowlist of permitted directories
        #   - Cannot read outside user's space
        #   - Cannot read system files (/etc, ~/.ssh, etc)
        #   See Milestone 9 in PROJECT-PLAN.md
        try:
            with open(filepath, 'r') as f:
                content = f.read()

            # Parse as JSON if requested
            if node.parse_json:
                import json
                try:
                    parsed = json.loads(content)
                    self.global_env.define(node.target, parsed)
                except json.JSONDecodeError as e:
                    raise RoshRuntimeError(f"Invalid JSON in {filepath}: {e}")
            else:
                # Store as string
                self.global_env.define(node.target, content)

        except FileNotFoundError:
            raise RoshRuntimeError(f"File not found: {filepath}")
        except Exception as e:
            raise RoshRuntimeError(f"Error reading file {filepath}: {e}")

    def eval_write(self, node: Write) -> None:
        """Execute: write <value> to <filepath>"""
        # Evaluate value
        value = self.eval_expression(node.value_expr)

        # Evaluate filepath
        filepath_value = self.eval_expression(node.filepath)
        filepath = rosh_to_python(filepath_value)

        if not isinstance(filepath, str):
            raise RoshTypeError(f"write requires a string filepath, got {type(filepath).__name__}")

        # TODO: For multi-user, implement filesystem restrictions
        #   - Allowlist of permitted directories
        #   - Cannot write outside user's space
        #   - Cannot overwrite system files
        #   See Milestone 9 in PROJECT-PLAN.md
        try:
            # Convert value to string for writing
            if isinstance(value, RoshObject):
                import json
                content = json.dumps(value.to_json(), indent=2)
            else:
                content = str(rosh_to_python(value))

            with open(filepath, 'w') as f:
                f.write(content)

        except Exception as e:
            raise RoshRuntimeError(f"Error writing to file {filepath}: {e}")

    def eval_import(self, node: Import) -> None:
        """Execute: import <module_path> - Import and execute a Rosh module or TOML file

        For .toml files: Creates a variable with the parsed TOML structure
        For .rosh files: Executes the code

        Use import "!path" to force reload (clears cache for that module)
        Example: import "!stdlib/mud.rosh" will reload even if already imported
        """
        # Extract variable name and file path from node
        # Supports: import toml from "file.toml" or import "file.rosh"
        var_name = None
        if hasattr(node, 'variable_name') and node.variable_name:
            var_name = node.variable_name

        # Handle module path - if it's an identifier, use it as a literal string
        # This allows: import mud (without quotes)
        if isinstance(node.module_path, Identifier):
            module_path = node.module_path.name
            # If no explicit variable name, use the identifier as variable name
            if var_name is None:
                var_name = module_path
        else:
            # Otherwise evaluate as expression (allows import "path/to/file")
            module_path_value = self.eval_expression(node.module_path)
            module_path = rosh_to_python(module_path_value)

            if not isinstance(module_path, str):
                raise RoshTypeError(f"import requires a string path, got {type(module_path).__name__}")

        # Check for force reload prefix (v0.0.4+)
        force_reload = module_path.startswith('!')
        if force_reload:
            module_path = module_path[1:]  # Strip the ! prefix
            print(f"🔄 Force reloading: {module_path}")

        # Resolve and fetch the module
        resolved_path = self._resolve_module_path(module_path)

        # Check if it's a TOML file
        if resolved_path.endswith('.toml'):
            # Extract variable name from filename if not provided
            if var_name is None:
                from pathlib import Path
                # Use filename without extension as variable name
                var_name = Path(resolved_path).stem
            self._import_toml(resolved_path, var_name)
            return

        # Check if already imported (simple caching for .rosh files)
        if not hasattr(self, '_imported_modules'):
            self._imported_modules = set()

        # Force reload: remove from cache
        if force_reload and resolved_path in self._imported_modules:
            self._imported_modules.remove(resolved_path)

        if resolved_path in self._imported_modules:
            return  # Already imported

        # Read and execute the Rosh module
        try:
            with open(resolved_path, 'r') as f:
                module_code = f.read()

            # Execute in current environment
            self._execute_code_string(module_code)

            # Mark as imported
            self._imported_modules.add(resolved_path)

        except FileNotFoundError:
            raise RoshRuntimeError(f"Module not found: {module_path}")
        except Exception as e:
            raise RoshRuntimeError(f"Error importing module {module_path}: {e}")

    def _import_toml(self, filepath: str, var_name: str):
        """Import a TOML file and create a variable with its contents

        Args:
            filepath: Path to the .toml file
            var_name: Name of the variable to create (e.g., 'toml', 'config')
        """
        try:
            # Try to use tomllib (Python 3.11+) or tomli (backport)
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib

            # Check file size (10MB limit for security)
            import os
            file_size = os.path.getsize(filepath)
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                raise RoshRuntimeError(
                    f"TOML file too large: {file_size} bytes (max {max_size})\n"
                    f"File: {filepath}"
                )

            # Read and parse TOML
            with open(filepath, 'rb') as f:
                toml_data = tomllib.load(f)

            # Convert to Rosh values
            rosh_data = self._toml_to_rosh(toml_data)

            # Create variable with the data
            self.current_env.define(var_name, rosh_data)

        except ImportError:
            raise RoshRuntimeError(
                "TOML support not installed. Run: pip install tomli"
            )
        except FileNotFoundError:
            raise RoshRuntimeError(f"TOML file not found: {filepath}")
        except Exception as e:
            raise RoshRuntimeError(f"Error importing TOML file {filepath}: {e}")

    def _toml_to_rosh(self, toml_value: Any) -> Any:
        """Convert TOML value to Rosh value

        Mappings:
        - TOML table → RoshObject
        - TOML array → Python list
        - TOML string/int/float/bool → Direct mapping
        - TOML datetime → ISO 8601 string
        """
        if isinstance(toml_value, dict):
            # TOML table → RoshObject
            obj = RoshObject(name="object")
            for key, value in toml_value.items():
                obj.set(key, self._toml_to_rosh(value))
            return obj
        elif isinstance(toml_value, list):
            # TOML array → Python list
            return [self._toml_to_rosh(item) for item in toml_value]
        elif hasattr(toml_value, 'isoformat'):
            # TOML datetime → ISO 8601 string
            return toml_value.isoformat()
        else:
            # Primitives: string, int, float, bool
            return toml_value

    def _resolve_module_path(self, module_path: str) -> str:
        """Resolve a module path to an actual file path

        Note: Remote URL imports have been removed for security.
        Use git submodules or local files for sharing code.
        """
        import os
        from pathlib import Path

        # Remote imports disabled for security - VR/AR worlds are offline-first
        if module_path.startswith('http://') or module_path.startswith('https://'):
            raise RoshRuntimeError(
                f"Remote URL imports are not supported for security.\n"
                f"Attempted to import: {module_path}\n\n"
                f"Instead:\n"
                f"  1. Download: curl {module_path} -o module.rosh\n"
                f"  2. Inspect: cat module.rosh  # READ THE CODE!\n"
                f"  3. Import: import \"module.rosh\"\n\n"
                f"For shared code, use git submodules or local package directories."
            )

        rosh_install_dir = Path(__file__).parent.parent.parent

        # If it's an absolute path or has path separators, treat as file path
        if os.path.isabs(module_path) or '/' in module_path or '\\' in module_path:
            # Resolve relative to current directory
            if module_path.endswith(('.rosh', '.toml')):
                candidate = Path(module_path)
            else:
                # Try .rosh first, then .toml
                candidate = Path(f"{module_path}.rosh")
                if not candidate.exists():
                    candidate = Path(f"{module_path}.toml")

            if candidate.exists():
                return str(candidate.resolve())
            # Also try without adding extension
            candidate = Path(module_path)
            if candidate.exists():
                return str(candidate.resolve())

            # Also try relative to the Rosh installation directory (handles 'stdlib/...').
            candidate = rosh_install_dir / module_path
            if candidate.exists():
                return str(candidate.resolve())
            if not module_path.endswith('.rosh'):
                candidate = rosh_install_dir / f"{module_path}.rosh"
                if candidate.exists():
                    return str(candidate.resolve())
            if not module_path.endswith('.toml'):
                candidate = rosh_install_dir / f"{module_path}.toml"
                if candidate.exists():
                    return str(candidate.resolve())

        # Otherwise, look in package directories
        package_dirs = [
            Path.home() / '.rosh' / 'packages',  # User packages
            Path.cwd(),  # Current directory
            rosh_install_dir / 'stdlib',  # Standard library
        ]

        # Try each package directory
        for pkg_dir in package_dirs:
            # If already has extension, try as-is first
            if module_path.endswith(('.rosh', '.toml')):
                candidate = pkg_dir / module_path
                if candidate.exists():
                    return str(candidate)

            # Try as directory with same name
            candidate = pkg_dir / module_path / f"{module_path}.rosh"
            if candidate.exists():
                return str(candidate)

            # Try as direct file (.rosh first, then .toml)
            if not module_path.endswith('.rosh'):
                candidate = pkg_dir / f"{module_path}.rosh"
                if candidate.exists():
                    return str(candidate)

            if not module_path.endswith('.toml'):
                candidate = pkg_dir / f"{module_path}.toml"
                if candidate.exists():
                    return str(candidate)

        # Not found
        raise RoshRuntimeError(f"Module '{module_path}' not found in package directories")

    def _suggest_fix_with_ai(self, error_msg: str, code_context: str = "") -> Optional[str]:
        """Use AI to suggest fixes for errors (if API key available)"""
        try:
            config = get_config()
            api_key = config.get_ai_key()

            if not api_key:
                return None  # No AI available

            provider_name = config.get('ai.provider', 'openai')
            model = config.get('ai.model')
            provider = get_provider(provider_name, api_key, model)

            # Ask AI for help
            prompt = f"""You are a helpful Rosh programming assistant. A user encountered this error:

Error: {error_msg}

{f"Code context: {code_context}" if code_context else ""}

Provide a brief, friendly suggestion (1-2 sentences) on how to fix this error.
Focus on the specific syntax or concept they need to correct."""

            suggestion = provider.prompt(prompt, {})
            return suggestion.strip()

        except Exception:
            # If AI fails, just return None
            return None

    def _deserialize_value(self, value):
        """Deserialize a JSON value back to a Rosh value"""
        from .values import RoshObject

        if isinstance(value, dict):
            if value.get("_type") == "object":
                # Reconstruct RoshObject
                obj = RoshObject(value["_name"])
                # Restore UUID and ID if present
                if "_uuid" in value:
                    obj.uuid = value["_uuid"]
                if "_id" in value:
                    obj.id = value["_id"]
                for key, val in value.items():
                    if not key.startswith("_"):
                        obj.set(key, self._deserialize_value(val))
                return obj
            elif value.get("_type") == "function":
                # Functions can't be fully restored from JSON
                # Show warning but don't fail - just skip this function
                print(f"⚠️  Warning: Function '{value['name']}' was not restored (function bodies cannot be serialized)")
                return None  # Will be skipped by caller
            else:
                # Regular dict (shouldn't happen in current Rosh)
                return value
        else:
            # Primitive value (number, string, boolean, null)
            return value

    def eval_stack_op(self, node: StackOp) -> None:
        """Execute stack operations: add, subtract, multiply, divide, dup, swap, drop

        Math ops: Pop two values from stack, perform operation, push result
        Manipulation: dup (duplicate TOS), swap (swap top 2), drop (remove TOS)
        """
        # Stack manipulation operations
        if node.operator == 'dup':
            if len(self.data_stack) < 1:
                raise RoshRuntimeError(f"Stack operation 'dup' requires 1 value, but stack is empty")
            value = self.data_stack[-1]  # Peek at top
            self.data_stack.append(value)  # Duplicate it
            return

        elif node.operator == 'swap':
            if len(self.data_stack) < 2:
                raise RoshRuntimeError(f"Stack operation 'swap' requires 2 values, but stack has {len(self.data_stack)}")
            # Swap top two elements
            self.data_stack[-1], self.data_stack[-2] = self.data_stack[-2], self.data_stack[-1]
            return

        elif node.operator == 'drop':
            if len(self.data_stack) < 1:
                raise RoshRuntimeError(f"Stack operation 'drop' requires 1 value, but stack is empty")
            self.data_stack.pop()
            return

        # Math operations (require 2 operands)
        if len(self.data_stack) < 2:
            raise RoshRuntimeError(f"Stack operation '{node.operator}' requires 2 values, but stack has {len(self.data_stack)}")

        # Pop operands (note order: first pop is right, second is left)
        right = self.data_stack.pop()
        left = self.data_stack.pop()

        # Convert to Python values for arithmetic
        left_val = rosh_to_python(left)
        right_val = rosh_to_python(right)

        # Perform operation
        if node.operator == 'add':
            result = left_val + right_val
        elif node.operator == 'subtract':
            result = left_val - right_val
        elif node.operator == 'multiply':
            result = left_val * right_val
        elif node.operator == 'divide':
            if right_val == 0:
                raise RoshRuntimeError("Division by zero")
            result = left_val / right_val
        else:
            raise RoshRuntimeError(f"Unknown stack operation: {node.operator}")

        # Push result back onto stack
        self.data_stack.append(result)

    def eval_if(self, node: IfStatement) -> None:
        """Execute: if <condition> then ... end"""
        condition_value = self.eval_expression(node.condition)

        if is_truthy(condition_value):
            for statement in node.then_body:
                self.eval_statement(statement)
        elif node.else_body:
            for statement in node.else_body:
                self.eval_statement(statement)

    def eval_while(self, node: WhileLoop) -> None:
        """Execute: while <condition> then ... end"""
        from .errors import BreakLoop, ContinueLoop

        while True:
            condition_value = self.eval_expression(node.condition)
            if not is_truthy(condition_value):
                break

            try:
                for statement in node.body:
                    self.eval_statement(statement)
            except BreakLoop:
                break
            except ContinueLoop:
                continue

    def eval_for(self, node) -> None:
        """Execute: for <var> in <start> to <end> [step <step>] then ... end

        Supports two modes:
        1. Range-based: for i in 1 to 10 [step 2] then ... end
        2. Collection-based: for item in all items then ... end
        """
        from .errors import BreakLoop, ContinueLoop

        # Calculate iteration count for batch mode decision
        iteration_count = 0

        if node.is_collection:
            # Collection-based iteration: for item in my_list OR for item in all items
            # Check if this is "for...in all <type>" - parser consumed "all" but we need to get all instances
            from .ast_nodes import Identifier
            if isinstance(node.start, Identifier):
                # Check if there are instances of this type
                type_name = node.start.name
                # Try plural-to-singular conversion if exact match not found
                actual_type = self._find_type_with_plural(type_name)
                if actual_type and len(self.instances.get(actual_type, [])) > 0:
                    # Use all instances of this type
                    items = self.instances[actual_type]
                else:
                    # Fall back to evaluating as expression
                    collection = self.eval_expression(node.start)
                    if isinstance(collection, list):
                        items = collection
                    else:
                        items = [collection]
            else:
                # Evaluate as expression (could be a list variable)
                collection = self.eval_expression(node.start)

                # Check if it's a list - direct list iteration
                if isinstance(collection, list):
                    items = collection
                # Check if it's object instances (from "all type")
                elif isinstance(collection, dict):
                    # If it's an object dict, iterate over properties
                    items = list(collection.values())
                # Check if we have multiple object instances
                elif hasattr(collection, '__iter__') and not isinstance(collection, str):
                    items = list(collection)
                else:
                    # Single value - treat as single-item list
                    items = [collection]

            iteration_count = len(items)

            # Enable batch mode if > 10 iterations (suppress per-item feedback)
            use_batch = self.interactive and iteration_count > 10
            if use_batch:
                self.batch_mode = True
                self.batch_creates = {}

            # Iterate over each item
            for item in items:
                # Set loop variable to current item (define creates or updates)
                self.current_env.define(node.variable, item)

                # Execute loop body
                try:
                    for statement in node.body:
                        self.eval_statement(statement)
                except BreakLoop:
                    break
                except ContinueLoop:
                    continue

            # Show batch summary
            if use_batch:
                self.batch_mode = False
                self._show_batch_summary()
        else:
            # Range-based iteration: for i in start to end [step X]
            start_val = self.eval_expression(node.start)
            end_val = self.eval_expression(node.end)
            step_val = self.eval_expression(node.step) if node.step else 1

            # Ensure numeric values
            if not isinstance(start_val, (int, float)):
                raise RoshRuntimeError(f"For loop start must be a number, got {type(start_val).__name__}")
            if not isinstance(end_val, (int, float)):
                raise RoshRuntimeError(f"For loop end must be a number, got {type(end_val).__name__}")
            if not isinstance(step_val, (int, float)):
                raise RoshRuntimeError(f"For loop step must be a number, got {type(step_val).__name__}")

            # Calculate iteration count
            if step_val > 0:
                iteration_count = max(0, int((end_val - start_val) / step_val) + 1)
            elif step_val < 0:
                iteration_count = max(0, int((start_val - end_val) / abs(step_val)) + 1)
            else:
                raise RoshRuntimeError("For loop step cannot be zero")

            # Enable batch mode if > 10 iterations
            use_batch = self.interactive and iteration_count > 10
            if use_batch:
                self.batch_mode = True
                self.batch_creates = {}

            # Handle positive or negative steps
            if step_val > 0:
                current = start_val
                while current <= end_val:
                    # Set loop variable to current value (define creates or updates)
                    self.current_env.define(node.variable, current)

                    # Execute loop body
                    try:
                        for statement in node.body:
                            self.eval_statement(statement)
                    except BreakLoop:
                        break
                    except ContinueLoop:
                        pass  # Just continue to next iteration

                    current += step_val
            elif step_val < 0:
                current = start_val
                while current >= end_val:
                    # Set loop variable to current value (define creates or updates)
                    self.current_env.define(node.variable, current)

                    # Execute loop body
                    try:
                        for statement in node.body:
                            self.eval_statement(statement)
                    except BreakLoop:
                        break
                    except ContinueLoop:
                        pass  # Just continue to next iteration

                    current += step_val

            # Show batch summary
            if use_batch:
                self.batch_mode = False
                self._show_batch_summary()

    def _show_batch_summary(self):
        """Show summary of batch operations (creates, etc.)"""
        for type_name, count in self.batch_creates.items():
            plural = self._pluralize(type_name, count)
            self.color_out.success(f"Created {count} {plural}")
        self.batch_creates = {}

    def eval_when_statement(self, node: WhenStatement) -> None:
        """Register an event handler

        Captures the lexical environment at registration time so handlers
        can access local variables from their defining scope.

        Example:
            when player_died then
                print "Game Over!"
            end

            when combat_start attacker defender then
                print "Combat begins!"
            end
        """
        event_name = node.event_name

        # Store handler definition with CAPTURED ENVIRONMENT (lexical scoping)
        handler = {
            'parameters': node.parameters,
            'body': node.body,
            'line': node.line,
            'captured_env': self.current_env  # Capture environment at registration time
        }

        # Register handler (multiple handlers per event supported)
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []

        self.event_handlers[event_name].append(handler)

    def eval_trigger_event(self, node: TriggerEvent) -> None:
        """Trigger an event, executing all registered handlers

        Examples:
            trigger player_died
            trigger combat_start with goblin player
        """
        event_name = node.event_name

        # Evaluate arguments
        args = [self.eval_expression(arg) for arg in node.arguments]

        # Get all handlers for this event
        handlers = self.event_handlers.get(event_name, [])

        if not handlers:
            # No handlers registered - silently continue
            return

        # Execute each handler
        for handler in handlers:
            parameters = handler['parameters']
            body = handler['body']
            captured_env = handler['captured_env']  # Environment at registration time

            # Create new environment for handler execution
            # Use CAPTURED environment as parent (lexical scoping)
            handler_env = Environment(parent=captured_env)

            # Bind arguments to parameters
            for i, param in enumerate(parameters):
                if i < len(args):
                    handler_env.define(param, args[i])
                else:
                    # Not enough arguments - bind to null
                    handler_env.define(param, None)

            # Execute handler body in new environment
            prev_env = self.current_env
            self.current_env = handler_env

            try:
                for statement in body:
                    self.eval_statement(statement)
            finally:
                # Restore previous environment
                self.current_env = prev_env

    def eval_metadata(self, node: Metadata) -> None:
        """Process program metadata declaration

        Examples:
            meta
                version "1.0.0"
                author "rdubar"
            end

            meta.generated
                # Auto-generates UUID, checksum, timestamps
            end
        """
        scope = node.scope or 'core'  # Default to 'core' if no scope specified

        # Evaluate all field expressions
        fields = {}
        for key, value_expr in node.fields.items():
            fields[key] = self.eval_expression(value_expr)

        # Auto-generate fields for 'generated' scope
        if scope == 'generated':
            # Generate UUID if not provided
            if 'uuid' not in fields:
                fields['uuid'] = self._generate_uuid()

            # Generate checksum if not provided
            if 'checksum' not in fields:
                if self.source_code:
                    fields['checksum'] = self._calculate_checksum()
                else:
                    # No source code available - warn user
                    print("⚠️  WARNING: Cannot generate checksum - source code not available (REPL mode?)",
                          file=sys.stderr)
                    fields['checksum'] = None

            # Set created timestamp if not provided
            if 'created' not in fields:
                from datetime import datetime
                fields['created'] = datetime.utcnow().isoformat() + 'Z'

        # Store metadata by scope
        self.program_metadata[scope] = fields

        # Make metadata accessible as 'meta' variable
        # Create a meta object that can be accessed like: get meta.version
        if 'meta' not in self.current_env.bindings:
            meta_obj = RoshObject('meta')
            self.current_env.define('meta', meta_obj)
        else:
            meta_obj = self.current_env.get('meta')

        # Set fields on meta object based on scope
        if scope == 'core' or scope is None:
            # Core metadata goes directly on meta object
            for key, value in fields.items():
                meta_obj.set(key, value)
        else:
            # Scoped metadata goes in a sub-object (meta.generated, meta.game, etc.)
            if not meta_obj.has(scope):
                scope_obj = RoshObject(scope)
                meta_obj.set(scope, scope_obj)
            else:
                scope_obj = meta_obj.get(scope)

            for key, value in fields.items():
                scope_obj.set(key, value)

    def _generate_uuid(self) -> str:
        """Generate a UUID4 for program identification"""
        import uuid
        return str(uuid.uuid4())

    def _calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of program source code"""
        if not self.source_code:
            raise RoshRuntimeError(
                "Cannot calculate checksum: source code not available. "
                "Checksums can only be generated when running from files."
            )

        import hashlib
        code_hash = hashlib.sha256(self.source_code.encode('utf-8')).hexdigest()
        return f"sha256:{code_hash}"

    def eval_comparison(self, node: Comparison) -> bool:
        """Evaluate comparison operations"""
        left = self.eval_expression(node.left)
        right = self.eval_expression(node.right)

        if node.operator == 'equal':
            return left == right
        elif node.operator == 'not_equal':
            return left != right
        elif node.operator == 'below':
            return left < right
        elif node.operator == 'above':
            return left > right
        else:
            raise RoshRuntimeError(f"Unknown comparison operator: {node.operator}")

    def eval_contains(self, node) -> bool:
        """Evaluate contains operation for strings and lists"""
        container = self.eval_expression(node.container)
        item = self.eval_expression(node.item)

        if isinstance(container, str):
            # String contains substring
            if not isinstance(item, str):
                item = str(item)  # Convert to string for comparison
            return item in container
        elif isinstance(container, list):
            # List contains item
            return item in container
        else:
            raise RoshTypeError(f"Cannot use 'contains' on type: {type(container).__name__}")

    def eval_logical_op(self, node) -> bool:
        """Evaluate logical operations (AND, OR, NOT)"""
        if node.operator == 'not':
            # NOT is a unary operator
            operand = self.eval_expression(node.right)
            return not is_truthy(operand)
        elif node.operator == 'and':
            # AND with short-circuit evaluation
            left = self.eval_expression(node.left)
            if not is_truthy(left):
                return False
            right = self.eval_expression(node.right)
            return is_truthy(right)
        elif node.operator == 'or':
            # OR with short-circuit evaluation
            left = self.eval_expression(node.left)
            if is_truthy(left):
                return True
            right = self.eval_expression(node.right)
            return is_truthy(right)
        else:
            raise RoshRuntimeError(f"Unknown logical operator: {node.operator}")

    def eval_random(self, node) -> Any:
        """Evaluate random number generation: random or random 1 to 6"""
        import random

        if node.min_val is not None and node.max_val is not None:
            # Random integer in range [min, max] (inclusive)
            min_value = self.eval_expression(node.min_val)
            max_value = self.eval_expression(node.max_val)

            if not isinstance(min_value, (int, float)):
                raise RoshTypeError(f"Random min must be a number, got {type(min_value).__name__}")
            if not isinstance(max_value, (int, float)):
                raise RoshTypeError(f"Random max must be a number, got {type(max_value).__name__}")

            # Convert to integers
            min_int = int(min_value)
            max_int = int(max_value)

            if min_int > max_int:
                raise RoshRuntimeError(f"Random min ({min_int}) cannot be greater than max ({max_int})")

            return random.randint(min_int, max_int)
        else:
            # Random float in range [0.0, 1.0)
            return random.random()

    def eval_length(self, node) -> int:
        """Evaluate length of string or list"""
        target_value = self.eval_expression(node.target)

        if isinstance(target_value, (str, list)):
            return len(target_value)
        else:
            raise RoshTypeError(f"Cannot get length of type: {type(target_value).__name__}")

    def eval_string_method(self, node) -> Any:
        """Evaluate string manipulation methods"""
        target_value = self.eval_expression(node.target)

        # Ensure target is a string
        if not isinstance(target_value, str):
            raise RoshTypeError(f"String method '{node.method}' requires a string, got {type(target_value).__name__}")

        # Evaluate all arguments
        args = [self.eval_expression(arg) for arg in node.args]

        # Execute the appropriate method
        if node.method == 'split':
            # split text by delimiter
            if len(args) != 1:
                raise RoshRuntimeError(f"split requires 1 argument (delimiter), got {len(args)}")
            delimiter = args[0]
            if not isinstance(delimiter, str):
                raise RoshTypeError(f"split delimiter must be a string, got {type(delimiter).__name__}")
            return target_value.split(delimiter)

        elif node.method == 'substring':
            # substring of text from start length len
            if len(args) != 2:
                raise RoshRuntimeError(f"substring requires 2 arguments (start, length), got {len(args)}")
            start = args[0]
            length = args[1]
            if not isinstance(start, (int, float)):
                raise RoshTypeError(f"substring start must be a number, got {type(start).__name__}")
            if not isinstance(length, (int, float)):
                raise RoshTypeError(f"substring length must be a number, got {type(length).__name__}")
            start = int(start)
            length = int(length)
            return target_value[start:start+length]

        elif node.method == 'lowercase':
            # lowercase of text
            if len(args) != 0:
                raise RoshRuntimeError(f"lowercase takes no arguments, got {len(args)}")
            return target_value.lower()

        elif node.method == 'uppercase':
            # uppercase of text
            if len(args) != 0:
                raise RoshRuntimeError(f"uppercase takes no arguments, got {len(args)}")
            return target_value.upper()

        elif node.method == 'trim':
            # trim text
            if len(args) != 0:
                raise RoshRuntimeError(f"trim takes no arguments, got {len(args)}")
            return target_value.strip()

        elif node.method == 'indexOf':
            # indexOf search in text
            if len(args) != 1:
                raise RoshRuntimeError(f"indexOf requires 1 argument (search string), got {len(args)}")
            search = args[0]
            if not isinstance(search, str):
                raise RoshTypeError(f"indexOf search must be a string, got {type(search).__name__}")
            result = target_value.find(search)
            return result  # Returns -1 if not found

        elif node.method == 'lastIndexOf':
            # lastIndexOf search in text
            if len(args) != 1:
                raise RoshRuntimeError(f"lastIndexOf requires 1 argument (search string), got {len(args)}")
            search = args[0]
            if not isinstance(search, str):
                raise RoshTypeError(f"lastIndexOf search must be a string, got {type(search).__name__}")
            result = target_value.rfind(search)
            return result  # Returns -1 if not found

        else:
            raise RoshRuntimeError(f"Unknown string method: {node.method}")

    def eval_unary_op(self, node) -> Any:
        """Evaluate unary operations (currently just negation)"""
        operand_value = self.eval_expression(node.operand)

        if node.operator == 'minus':
            # Negate the value
            if not isinstance(operand_value, (int, float)):
                raise RoshRuntimeError(f"Cannot negate non-numeric value: {type(operand_value).__name__}")
            return -operand_value
        else:
            raise RoshRuntimeError(f"Unknown unary operator: {node.operator}")

    def eval_binary_op(self, node: BinaryOp) -> Any:
        """Evaluate binary operations"""
        left = self.eval_expression(node.left)
        right = self.eval_expression(node.right)

        if node.operator == 'plus':
            # Auto-coerce mixed types to string with warning
            if isinstance(left, str) and not isinstance(right, str):
                print(f"⚠️  Warning: Converting {type(right).__name__} to string for concatenation")
                return left + str(right)
            elif isinstance(right, str) and not isinstance(left, str):
                print(f"⚠️  Warning: Converting {type(left).__name__} to string for concatenation")
                return str(left) + right
            return left + right
        elif node.operator == 'minus':
            return left - right
        elif node.operator == 'times':
            return left * right
        elif node.operator == 'divided_by':
            if right == 0:
                raise RoshRuntimeError("Division by zero")
            return left / right
        elif node.operator == 'modulo':
            if right == 0:
                raise RoshRuntimeError("Modulo by zero")
            return left % right
        else:
            raise RoshRuntimeError(f"Unknown binary operator: {node.operator}")

    def eval_function_def(self, node: FunctionDef) -> None:
        """Execute: define function <name> ... end"""
        func = RoshFunction(
            name=node.name,
            parameters=node.parameters,
            body=node.body,
            closure_env=self.current_env
        )
        self.current_env.define(node.name, func)

    def eval_return(self, node) -> None:
        """Execute: return [expression]"""
        from .errors import ReturnValue

        # Evaluate the return value if present
        if node.value is not None:
            value = self.eval_expression(node.value)
        else:
            value = None

        # Raise exception to unwind call stack
        raise ReturnValue(value)

    def eval_break(self, node) -> None:
        """Execute: break"""
        from .errors import BreakLoop
        raise BreakLoop()

    def eval_continue(self, node) -> None:
        """Execute: continue"""
        from .errors import ContinueLoop
        raise ContinueLoop()

    def eval_stop(self, node) -> None:
        """Execute: stop - terminates program execution"""
        from .errors import StopExecution
        raise StopExecution()

    def eval_function_call(self, node: FunctionCall) -> Any:
        """Execute: call <name> <args>"""
        from .errors import ReturnValue

        # Check for built-in functions first
        if node.name in BUILTIN_FUNCTIONS:
            builtin_func = BUILTIN_FUNCTIONS[node.name]
            arg_values = [self.eval_expression(arg) for arg in node.arguments]
            try:
                result = builtin_func(*arg_values)
                # If there's a result, push it onto the data stack
                if result is not None:
                    self.data_stack.append(result)
                return result
            except (TypeError, ValueError) as e:
                raise RoshRuntimeError(f"Error calling built-in function '{node.name}': {e}")

        # Check for user-defined functions
        func = self.current_env.get(node.name)

        if not isinstance(func, RoshFunction):
            raise RoshTypeError(f"Cannot call non-function: {node.name}")

        # Evaluate arguments
        arg_values = [self.eval_expression(arg) for arg in node.arguments]

        # Check argument count
        if len(arg_values) != len(func.parameters):
            raise RoshRuntimeError(
                f"Function {func.name} expects {len(func.parameters)} arguments, got {len(arg_values)}"
            )

        # Create new environment for function execution
        func_env = Environment(parent=func.closure_env)

        # Bind parameters
        for param_name, arg_value in zip(func.parameters, arg_values):
            func_env.define(param_name, arg_value)

        # Execute function body with return value handling
        old_env = self.current_env
        self.current_env = func_env

        result = None
        try:
            for statement in func.body:
                result = self.eval_statement(statement)
        except ReturnValue as ret:
            result = ret.value

        self.current_env = old_env

        # Push result to stack if not None
        if result is not None:
            self.data_stack.append(result)

        return result

    def eval_clone_object(self, node: CloneObject) -> None:
        """Execute: clone <source> as <target> - Deep copy an object
        If target is None, creates anonymous instance with auto-numbered ID
        If source doesn't exist but is a known object, create it first
        """
        # Check if source object exists
        if not self.current_env.exists(node.source):
            # Check if this is a known object we can create
            from .data import get_known_objects_text
            known_objects = get_known_objects_text()
            if node.source in known_objects:
                # Create from known object template
                # Use target name if provided (e.g., "create apple golden" → named "golden", type "apple")
                # Otherwise use source name (e.g., "clone apple" → named "apple")
                obj_name = node.target if node.target else node.source
                new_obj = RoshObject(name=obj_name)
                new_obj.set('object_type', node.source)  # Type is still the template type
                new_obj.set('description', known_objects[node.source])
                self.current_env.define(obj_name, new_obj)
                self.color_out.success(f"Created '{obj_name}'" + (f" (type: {node.source})" if node.target else ""))
                return
            else:
                raise RoshRuntimeError(f"Cannot clone: object '{node.source}' does not exist")

        # Get the source object
        source_obj = self.current_env.get(node.source)

        if not isinstance(source_obj, RoshObject):
            raise RoshTypeError(f"Cannot clone non-object: '{node.source}' is not an object")

        # Determine if anonymous (auto-numbered) or explicit name
        is_anonymous = node.target is None

        # Create a new object with the same parents
        # For anonymous instances, use template name as placeholder
        obj_name = node.target if node.target else node.source
        cloned_obj = RoshObject(name=obj_name, parents=source_obj.parents.copy())

        # Deep copy all property stacks from source
        import copy
        for prop_name, prop_stack in source_obj.property_stacks.items():
            # Deep copy the entire stack
            cloned_obj.property_stacks[prop_name] = copy.deepcopy(prop_stack)

        # Register instance
        if is_anonymous:
            # Auto-number: register without explicit name
            self.register_instance(cloned_obj, type_name=node.source, explicit_name=None)
            # Use the auto-generated ID as the variable name
            var_name = cloned_obj.id
        else:
            # Explicit name: register with given name
            self.register_instance(cloned_obj, type_name=node.source, explicit_name=node.target)
            var_name = node.target

        # Define the new object in the environment
        self.current_env.define(var_name, cloned_obj)
        binding_env = self.current_env
        binding_type = binding_env.bindings[var_name]['type']

        def undo_clone():
            if var_name in binding_env.bindings:
                existing = binding_env.bindings[var_name]['value']
                if existing is cloned_obj:
                    self._detach_object_instance(cloned_obj)
                    del binding_env.bindings[var_name]

        def redo_clone():
            binding_env.bindings[var_name] = {
                'value': cloned_obj,
                'type': binding_type
            }
            self._attach_object_instance(cloned_obj)

        self.push_undo(f"clone {node.source}", undo_clone, redo_clone)

        # Print feedback
        if is_anonymous:
            instances = self.instances.get(node.source, [])
            count = len(instances)
            # Get the instance number from the ID (e.g., "thing-3" → 3)
            instance_num = int(cloned_obj.id.split('-')[-1])
            self.color_out.success(f"Cloned '{node.source}' as '{cloned_obj.id}'")
        else:
            self.color_out.success(f"Cloned '{node.source}' as '{node.target}'")

    def eval_delete_object(self, node: DeleteObject) -> None:
        """Execute: delete <name> - Remove an object from environment"""
        # Block deletion of reserved objects
        if node.name == 'meta':
            raise RoshRuntimeError("Cannot delete 'meta': meta is a reserved implicit object")

        # Check if the object exists
        if not self.current_env.exists(node.name):
            raise RoshRuntimeError(f"Cannot delete: '{node.name}' does not exist")

        env = self._find_env_for_binding(node.name) or self.current_env
        binding = env.bindings.get(node.name)
        obj = binding['value']
        binding_type = binding['type']

        # Clean up instance tracking if this is a RoshObject
        if isinstance(obj, RoshObject):
            self._detach_object_instance(obj)

        # Remove from environment
        if node.name in env.bindings:
            del env.bindings[node.name]
            self.color_out.success(f"Deleted '{node.name}'")
        else:
            raise RoshRuntimeError(f"Cannot delete: '{node.name}' is not in current scope")

        def undo_delete(target_env=env, name=node.name, value=obj, value_type=binding_type):
            target_env.bindings[name] = {
                'value': value,
                'type': value_type
            }
            if isinstance(value, RoshObject):
                self._attach_object_instance(value)

        def redo_delete(target_env=env, name=node.name, value=obj):
            if name in target_env.bindings:
                existing = target_env.bindings[name]['value']
                if isinstance(existing, RoshObject):
                    self._detach_object_instance(existing)
                del target_env.bindings[name]

        self.push_undo(f"delete {node.name}", undo_delete, redo_delete)

    def eval_reset_object(self, node: ResetObject) -> None:
        """Execute: reset <name> - Revert object to template defaults"""
        # Check if the object exists
        if not self.current_env.exists(node.name):
            raise RoshRuntimeError(f"Cannot reset: '{node.name}' does not exist")

        obj = self.current_env.get(node.name)
        if not isinstance(obj, RoshObject):
            raise RoshTypeError(f"Cannot reset non-object: '{node.name}'")

        # Save current state for undo
        old_stacks = {k: list(v) for k, v in obj.property_stacks.items()}

        # Clear all property stacks - object will inherit from template
        obj.property_stacks.clear()

        self.color_out.success(f"Reset '{node.name}' to defaults")

        def undo_reset(target_obj=obj, saved_stacks=old_stacks):
            target_obj.property_stacks = {k: list(v) for k, v in saved_stacks.items()}

        def redo_reset(target_obj=obj):
            target_obj.property_stacks.clear()

        self.push_undo(f"reset {node.name}", undo_reset, redo_reset)

    def eval_hide_object(self, node: HideObject) -> None:
        """Execute: hide <name> - Set object visible to false"""
        # Check if the object exists
        if not self.current_env.exists(node.name):
            raise RoshRuntimeError(f"Cannot hide: '{node.name}' does not exist")

        obj = self.current_env.get(node.name)
        if not isinstance(obj, RoshObject):
            raise RoshTypeError(f"Cannot hide non-object: '{node.name}'")

        # Save current visibility for undo
        old_visible = obj.get('visible') if obj.has('visible') else True

        # Set visible to false
        obj.set('visible', False)

        self.color_out.success(f"Hid '{node.name}'")

        def undo_hide(target_obj=obj, saved_visible=old_visible):
            target_obj.set('visible', saved_visible)

        def redo_hide(target_obj=obj):
            target_obj.set('visible', False)

        self.push_undo(f"hide {node.name}", undo_hide, redo_hide)

    def eval_show_object(self, node: ShowObject) -> None:
        """Execute: show <name> - Set object visible to true"""
        # Check if the object exists
        if not self.current_env.exists(node.name):
            raise RoshRuntimeError(f"Cannot show: '{node.name}' does not exist")

        obj = self.current_env.get(node.name)
        if not isinstance(obj, RoshObject):
            raise RoshTypeError(f"Cannot show non-object: '{node.name}'")

        # Save current visibility for undo
        old_visible = obj.get('visible') if obj.has('visible') else True

        # Set visible to true
        obj.set('visible', True)

        self.color_out.success(f"Showed '{node.name}'")

        def undo_show(target_obj=obj, saved_visible=old_visible):
            target_obj.set('visible', saved_visible)

        def redo_show(target_obj=obj):
            target_obj.set('visible', True)

        self.push_undo(f"show {node.name}", undo_show, redo_show)

    def eval_count_objects(self, node: CountObjects) -> None:
        """Execute: count [type] - Count objects, optionally by type"""
        # Get all objects from the current environment (traverse up the scope chain)
        all_objects = []
        env = self.current_env
        seen_names = set()
        while env is not None:
            for name, binding in env.bindings.items():
                if name not in seen_names:
                    seen_names.add(name)
                    value = binding['value']
                    if isinstance(value, RoshObject):
                        all_objects.append((name, value))
            env = env.parent

        if node.object_type is None:
            # Count all objects
            count = len(all_objects)
            self.color_out.info(f"{count} object{'s' if count != 1 else ''} in scope")
        else:
            # Count objects matching the type
            type_name = node.object_type
            # Handle plurals
            if type_name.endswith('ies'):
                type_name = type_name[:-3] + 'y'
            elif type_name.endswith('es') and (type_name.endswith('xes') or type_name.endswith('shes') or type_name.endswith('ches')):
                type_name = type_name[:-2]
            elif type_name.endswith('s') and not type_name.endswith('ss'):
                type_name = type_name[:-1]

            # Find matches - check name, _type property, or extract from name
            import re
            matches = []
            for name, obj in all_objects:
                obj_type = None
                if obj.has('_type'):
                    obj_type = obj.get('_type')
                elif obj.parents:
                    # Use first parent's name as type
                    obj_type = obj.parents[0].name
                else:
                    # Try to extract type from name like "banana-1" -> "banana"
                    match = re.match(r'^(.+?)-\d+$', name)
                    obj_type = match.group(1) if match else name

                if obj_type == type_name or name == type_name:
                    matches.append(name)

            count = len(matches)
            if count == 0:
                self.color_out.dim(f"No {type_name} objects found")
            else:
                self.color_out.info(f"{count} {type_name} object{'s' if count != 1 else ''}:")
                # Show first 10, then "...N more"
                for name in matches[:10]:
                    self.color_out.print(f"  {name}")
                if count > 10:
                    self.color_out.dim(f"  ...{count - 10} more")

    def eval_move_object(self, node: MoveObject) -> None:
        """Execute: move <name> to x,y[,z] - Move object to coordinates"""
        # Check if the object exists
        if not self.current_env.exists(node.name):
            raise RoshRuntimeError(f"Cannot move: '{node.name}' does not exist")

        obj = self.current_env.get(node.name)
        if not isinstance(obj, RoshObject):
            raise RoshTypeError(f"Cannot move non-object: '{node.name}'")

        # Evaluate coordinates
        x = self.eval_expression(node.x)
        y = self.eval_expression(node.y)
        z = self.eval_expression(node.z) if node.z else None

        # Save old position for undo
        old_x = obj.get('x') if obj.has('x') else 0
        old_y = obj.get('y') if obj.has('y') else 0
        old_z = obj.get('z') if obj.has('z') else 0

        # Set new position
        obj.set('x', x)
        obj.set('y', y)
        if z is not None:
            obj.set('z', z)

        # Report the move
        if z is not None:
            self.color_out.success(f"Moved '{node.name}' to ({x}, {y}, {z})")
        else:
            self.color_out.success(f"Moved '{node.name}' to ({x}, {y})")

        def undo_move(target_obj=obj, sx=old_x, sy=old_y, sz=old_z):
            target_obj.set('x', sx)
            target_obj.set('y', sy)
            target_obj.set('z', sz)

        def redo_move(target_obj=obj, nx=x, ny=y, nz=z):
            target_obj.set('x', nx)
            target_obj.set('y', ny)
            if nz is not None:
                target_obj.set('z', nz)

        self.push_undo(f"move {node.name}", undo_move, redo_move)

    def eval_properties(self, node: PropertiesCommand) -> None:
        """Execute: properties <target> - List all properties of an object"""
        # Get the target object
        target_obj = self.current_env.get(node.target)

        if target_obj is None:
            raise RoshRuntimeError(f"Cannot show properties: '{node.target}' does not exist")

        if not isinstance(target_obj, RoshObject):
            raise RoshTypeError(f"Cannot show properties of non-object: '{node.target}'")

        # Collect all properties (own + inherited)
        all_props = {}

        # First, get inherited properties from parents (left-to-right)
        for parent in target_obj.parents:
            parent_props = self._get_all_properties(parent)
            all_props.update(parent_props)

        # Then, add own properties (these override inherited ones)
        for prop_name, prop_stack in target_obj.property_stacks.items():
            if prop_stack:  # Only show if stack is not empty
                all_props[prop_name] = (prop_stack[-1], 'own')

        # Mark inherited properties
        for prop_name in all_props:
            if prop_name not in target_obj.property_stacks or not target_obj.property_stacks[prop_name]:
                value = target_obj.get(prop_name)
                all_props[prop_name] = (value, 'inherited')

        # Display object metadata first
        self.color_out.print(f"Object: {node.target}", style="bold cyan")
        self.color_out.uuid(target_obj.uuid)
        if target_obj.id:
            self.color_out.object_id(target_obj.id)
        self.color_out.print()

        # Display properties
        if not all_props:
            self.color_out.print("  No properties", style="dim")
        else:
            self.color_out.print("Properties:", style="bold yellow")
            for prop_name, (value, source) in sorted(all_props.items()):
                # Format the value nicely
                if isinstance(value, RoshObject):
                    value_str = f"<object {value.name}>"
                elif isinstance(value, RoshFunction):
                    value_str = f"<function {value.name}>"
                elif isinstance(value, str):
                    value_str = f'"{value}"'
                elif value is None:
                    value_str = "null"
                elif isinstance(value, bool):
                    value_str = "true" if value else "false"
                else:
                    value_str = str(value)

                source_indicator = " (inherited)" if source == 'inherited' else ""
                prop_style = "cyan" if source == 'own' else "dim cyan"
                self.color_out.print(f"  {prop_name}: {value_str}{source_indicator}", style=prop_style)

    def _get_all_properties(self, obj: RoshObject, visited: set = None) -> dict:
        """Helper: Recursively get all properties from an object and its parents

        Args:
            obj: The object to get properties from
            visited: Set of UUIDs already visited (for cycle detection)

        Returns:
            Dictionary of property name -> value

        Raises:
            RoshRuntimeError: If a cycle is detected in the inheritance chain
        """
        if visited is None:
            visited = set()

        # Check for cycles
        if obj.uuid in visited:
            raise RoshRuntimeError(
                f"Circular inheritance detected: object '{obj.name}' (UUID: {obj.uuid}) "
                f"appears multiple times in its own inheritance chain"
            )

        visited.add(obj.uuid)
        props = {}

        # Get from parents first (so own properties override)
        for parent in obj.parents:
            props.update(self._get_all_properties(parent, visited))

        # Add own properties
        for prop_name, prop_stack in obj.property_stacks.items():
            if prop_stack:
                props[prop_name] = prop_stack[-1]

        return props

    def eval_goto(self, node: GotoRoom) -> None:
        """Execute: goto <room> - Move to a room and display description"""
        # Check if it's a direction from current room
        if node.room in ['north', 'south', 'east', 'west', 'up', 'down']:
            # Try to follow the direction from current room
            if self.current_env.exists('current-room'):
                current_room_name = self.current_env.get('current-room')
                current_room_obj = self.current_env.get(current_room_name)
                if isinstance(current_room_obj, RoshObject):
                    target_room_name = current_room_obj.get(node.room)
                    if target_room_name:
                        node = GotoRoom(room=target_room_name, line=node.line)
                    else:
                        print(f"You can't go {node.room} from here.", file=self.output_stream)
                        return

        # Get the room object
        room_obj = self.current_env.get(node.room)

        if room_obj is None:
            raise RoshRuntimeError(f"Cannot go to '{node.room}': space does not exist")

        if not isinstance(room_obj, RoshObject):
            raise RoshTypeError(f"Cannot go to '{node.room}': not a valid space")

        # Update current-room variable
        if self.current_env.exists('current-room'):
            self.current_env.set('current-room', node.room)
        else:
            self.current_env.define('current-room', node.room)

        # Display the room
        room_name = room_obj.get('name') or node.room
        room_desc = room_obj.get('description') or "You see nothing special."

        print(f"\n=== {room_name} ===", file=self.output_stream)
        print(room_desc, file=self.output_stream)

        # Show exits
        exits = []
        for direction in ['north', 'south', 'east', 'west', 'up', 'down']:
            exit_room = room_obj.get(direction)
            if exit_room and exit_room != 'null' and exit_room is not None:
                exits.append(direction)

        if exits:
            print(f"\nExits: {', '.join(exits)}", file=self.output_stream)
        else:
            print("\nNo obvious exits.", file=self.output_stream)
        print(file=self.output_stream)

    def eval_look(self, node: LookCommand) -> None:
        """Execute: look [object] - Show current room or examine object"""
        # If target specified, examine that object
        if node.target:
            # Same as properties command
            if not self.current_env.exists(node.target):
                raise RoshRuntimeError(f"Cannot look at '{node.target}': does not exist")

            obj = self.current_env.get(node.target)
            if not isinstance(obj, RoshObject):
                self.color_out.print(f"{node.target} = {obj}")
                return

            # Show object details
            self.color_out.print()
            self.color_out.header(f"=== {node.target} ===")
            self.color_out.print(f"Type: {obj.name}", style="cyan")
            self.color_out.uuid(obj.uuid)
            if obj.id:
                self.color_out.object_id(obj.id)

            # Show parents
            if obj.parents:
                parent_names = [p.name for p in obj.parents]
                self.color_out.print(f"Inherits from: {', '.join(parent_names)}", style="yellow")

            # Show properties
            self.color_out.print()
            for prop_name, prop_stack in obj.property_stacks.items():
                current_value = prop_stack[-1] if prop_stack else None
                if isinstance(current_value, str):
                    self.color_out.print(f"  {prop_name}: \"{current_value}\"", style="green")
                else:
                    self.color_out.print(f"  {prop_name}: {current_value}", style="green")
            return

        # No target - show current space
        if not self.current_env.exists('current-room'):
            print("You are nowhere. Use 'goto <space>' to go somewhere.", file=self.output_stream)
            return

        current_room_name = self.current_env.get('current-room')
        room_obj = self.current_env.get(current_room_name)

        if room_obj is None or not isinstance(room_obj, RoshObject):
            print(f"Error: Current room '{current_room_name}' no longer exists.", file=self.output_stream)
            return

        # Display the room (same as goto)
        room_name = room_obj.get('name') or current_room_name
        room_desc = room_obj.get('description') or "You see nothing special."

        print(f"\n=== {room_name} ===", file=self.output_stream)
        print(room_desc, file=self.output_stream)

        # Show exits
        exits = []
        for direction in ['north', 'south', 'east', 'west', 'up', 'down']:
            exit_room = room_obj.get(direction)
            if exit_room and exit_room != 'null' and exit_room is not None:
                exits.append(direction)

        if exits:
            print(f"\nExits: {', '.join(exits)}", file=self.output_stream)
        else:
            print("\nNo obvious exits.", file=self.output_stream)
        print(file=self.output_stream)

    def eval_connect(self, node: ConnectRooms) -> None:
        """Execute: connect <room1> <direction> <room2> - Connect two rooms bidirectionally"""
        # Get both rooms
        room1_obj = self.current_env.get(node.room1)
        room2_obj = self.current_env.get(node.room2)

        if room1_obj is None:
            raise RoshRuntimeError(f"Cannot connect: space '{node.room1}' does not exist")
        if room2_obj is None:
            raise RoshRuntimeError(f"Cannot connect: space '{node.room2}' does not exist")

        if not isinstance(room1_obj, RoshObject):
            raise RoshTypeError(f"Cannot connect: '{node.room1}' is not a valid space")
        if not isinstance(room2_obj, RoshObject):
            raise RoshTypeError(f"Cannot connect: '{node.room2}' is not a valid space")

        # Map directions to their opposites
        opposite_directions = {
            'north': 'south',
            'south': 'north',
            'east': 'west',
            'west': 'east',
            'up': 'down',
            'down': 'up'
        }

        # Set the forward connection
        room1_obj.set(node.direction, node.room2)

        # Set the reverse connection if we know the opposite direction
        opposite = opposite_directions.get(node.direction)
        if opposite:
            room2_obj.set(opposite, node.room1)
            print(f"Connected {node.room1} ({node.direction}) ↔ {node.room2} ({opposite})", file=self.output_stream)
        else:
            # Just one-way connection for non-standard directions
            print(f"Connected {node.room1} ({node.direction}) → {node.room2}", file=self.output_stream)
    def eval_help(self, node: Help) -> None:
        """Execute: help [topic] - Display context-aware help"""
        if node.topic is None:
            # Show list of all available commands
            print("🤖 Rosh Help - Available Commands", file=self.output_stream)
            print("=" * 50, file=self.output_stream)
            print(file=self.output_stream)

            # Group commands by category
            categories = {
                'Core': ['create', 'set', 'get', 'print'],
                'Objects': ['clone', 'delete', 'properties', 'props'],
                'Lists': ['append', 'remove', 'length', 'contains'],
                'Stack': ['stack', 'push', 'pop', 'add', 'subtract', 'multiply', 'divide', 'dup', 'swap', 'drop'],
                'Control Flow': ['if', 'while', 'for', 'break', 'continue', 'return', 'stop', 'exit'],
                'Functions': ['define', 'call'],
                'Strings': ['split', 'substring', 'lowercase', 'uppercase', 'trim', 'indexOf', 'lastIndexOf'],
                'Math': ['random', 'abs', 'min', 'max', 'round', 'floor', 'ceil', 'sqrt', 'pow', 'sin', 'cos', 'tan'],
                'I/O & Modules': ['import', 'read', 'write', 'save', 'eval', 'dump', 'load'],
                'MUD': ['goto', 'go', 'look', 'l', 'connect', 'link'],
                'AI': ['prompt'],
                'Help': ['help']
            }

            for category, commands in categories.items():
                print(f"{category}:", file=self.output_stream)
                for cmd in commands:
                    if cmd in self.help_registry:
                        # Show just the first line of help
                        first_line = self.help_registry[cmd].split('\n')[0]
                        print(f"  {cmd:15s} - {first_line}", file=self.output_stream)
                print(file=self.output_stream)

            print("Type 'help <command>' for detailed help on a specific command.", file=self.output_stream)
            print("Type 'help <object>' to see properties of an object.", file=self.output_stream)

        else:
            # Show help for a specific topic
            topic = node.topic

            # Check if it's a command in the help registry
            if topic in self.help_registry:
                print(f"Help: {topic}", file=self.output_stream)
                print("-" * 50, file=self.output_stream)
                print(self.help_registry[topic], file=self.output_stream)

            # Check if it's an object in the environment
            elif self.current_env.exists(topic):
                obj = self.current_env.get(topic)
                if isinstance(obj, RoshObject):
                    print(f"Object: {topic}", file=self.output_stream)
                    print("-" * 50, file=self.output_stream)
                    print(f"Type: {obj.name}", file=self.output_stream)
                    print(f"UUID: {obj.uuid}", file=self.output_stream)
                    if obj.id:
                        print(f"ID: {obj.id}", file=self.output_stream)

                    # Show parent chain
                    if obj.parents:
                        parent_names = [p.name for p in obj.parents]
                        print(f"Inherits from: {', '.join(parent_names)}", file=self.output_stream)

                    print(file=self.output_stream)
                    print("Properties:", file=self.output_stream)
                    for prop_name, prop_stack in obj.property_stacks.items():
                        current_value = prop_stack[-1] if prop_stack else None
                        print(f"  {prop_name}: {current_value}", file=self.output_stream)
                else:
                    print(f"{topic} = {obj}", file=self.output_stream)

            else:
                print(f"No help available for '{topic}'", file=self.output_stream)
                print(f"Try 'help' to see all available commands.", file=self.output_stream)
