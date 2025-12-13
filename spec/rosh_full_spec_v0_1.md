# Rosh Language Specification & Implementation Plan (Comprehensive Draft)

> **Status:** Draft v0.1  
> **Project:** Rosh – spoken-language-first, stack-based, AI-native programming language  
> **Scope:** Language vision, core model, syntax, examples, runtime architecture, and implementation roadmap (Python first, then Go & Elixir).

---

## 0. Project Context

Rosh is being designed as:

- **Spoken-language-first**: Optimized for dictation and natural phrasing, not just typing.
- **Stack-based**: Execution is driven by a data stack and a property stack, with concise commands.
- **JSON-native**: All state is stored as JSON-like objects with clear structure and inheritance.
- **AI-native**: The language includes a first-class `prompt` primitive that can consult AI using full program context.
- **Write-once, run-many**: Rosh code can be interpreted directly, or compiled/transpiled to Python, Go, Elixir, JavaScript, or others.
- **Prototyping-focused, but scalable**: Great for quickly sketching automation, tools, games, and simulations, but with enough structure to grow into larger systems.

This document is intended to be the **single source of truth** for:

- Language design and semantics
- Example programs and idioms
- Implementation architecture for the first interpreter (Python)
- Plans for Go and Elixir backends

---

## 1. Vision & Design Goals

### 1.1 High-Level Vision

Rosh is what you would get if you combined:

- The **composability and discipline** of a stack-based language (Forth, Factor)
- The **readability and pragmatism** of Python
- The **concurrency and robustness** of Go and Elixir
- The **assistive power** of an AI coding copilot baked into the language

The goal is to allow a programmer to **speak** a program into existence (literally or figuratively), with syntax that mirrors natural English, while still being precise enough to compile and run predictably.

### 1.2 Primary Goals

1. **Spoken-friendly syntax**  
   - Minimal punctuation and boilerplate.  
   - Commands read like imperative instructions: “create a player”, “set health to 100”, “if health is below zero then…”.  
   - Dictation and screenreader-friendly.

2. **JSON state as the foundation**  
   - All persistent state is represented as JSON-compatible values: objects/maps, arrays, numbers, strings, booleans, null.
   - This makes Rosh easy to interoperate with web APIs, databases, and other languages.

3. **Stack-based for power and composability**  
   - Eval model is a simple **data stack** plus **property stacks** per object.
   - You can write very terse code when you want to, or more English-like code when clarity matters.

4. **AI as a first-class citizen**  
   - The `prompt` command allows the program to query an AI model with context from the runtime.
   - AI is not magical: it’s a function that takes structured context and returns structured data (plus text).

5. **Write-once, run-many**  
   - Rosh source code should be portable.
   - Targets:
     - **Python**: reference interpreter, great for rapid prototyping.
     - **Go**: strong for CLI tools & games requiring performance and concurrency.
     - **Elixir**: strong for highly concurrent and distributed systems.

6. **Modular and layered complexity**  
   - Beginners can write simple scripts with minimal syntax.  
   - Advanced users can define schemas, types, property behaviors, and custom modules.

---

## 2. Core Conceptual Model

### 2.1 Value Types

All values in Rosh are JSON-compatible:

- **null**
- **boolean**: `true`, `false`
- **number**: integers and floats
- **string**
- **array** (list)
- **object** (map/dictionary)

Additional “virtual” types are layered on top but are representable in JSON:

- **Entity / object with schema**: An object with metadata about its type, schema, and property stacks.
- **Module**: Namespaced collection of objects and functions.

### 2.2 The Data Stack

Rosh programs execute in terms of a **data stack**:

- Many operations consume their inputs from the top of the stack and push their outputs.
- Spoken-language surface syntax *usually hides* the stack mechanics, but they are always there under the hood.

Examples (conceptual):

- `3 4 add` → push `3`, push `4`, apply `add` → `7` on stack.
- `"hello" "world" join-with-space` → `"hello world"`.

### 2.3 Objects and the Property Stack

Each Rosh object has:

- A **base JSON map** of properties.
- For each property `p`, a **property stack** tracking overrides over time.

Conceptually, for object `player` and property `health`:

- Base value: `player.health = 100`
- Property stack: `[100]` initially
- `push player health 50` pushes `50` on the property stack
- `current player health` returns `50`
- `pop player health` reverts to `100`

This is useful for:

- Temporary overrides (e.g. power-ups, buffs, environment overrides).
- Transaction-like behavior (push, modify, revert).
- Context-sensitive behavior (e.g. AI prompt with overrides).

### 2.4 Inheritance & Modules

Rosh supports a **prototype-based inheritance-ish** model over JSON:

- Objects can declare **one or more parents** (prototypes).
- Property lookup follows: `self` → `local overrides` → `parents (ordered)`.
- Parents are also JSON objects (or entity definitions).

Modules are:

- Namespaces of related objects and functions.
- Loadable as libraries: `import game.basic`.

### 2.5 AI Integration (`prompt`)

The `prompt` primitive:

- Has access to **current program state** (or a selected subset).
- Can receive a text prompt, plus structured context.
- Returns text plus optionally structured JSON.

Example conceptual form:

```rosh
prompt
  using player, world, recent_events
  ask "Given this situation, what should the NPC say next?"
  expect text as dialogue
into next_dialogue

say next_dialogue
```

The interpreter/runtime decides how to:

- Package context (which variables/objects to serialize).
- Call the actual AI model (local, remote, bridge to OpenAI, etc.).
- Parse structured responses when `expect` is specified.

---

## 3. Surface Syntax

Rosh aims to allow both **terse stack-style** and **English-like** syntax.

### 3.1 General Characteristics

- **Case-insensitive keywords** (by default, though implementation can preserve case for strings).
- Lines are sequences of **phrases**; semicolons or newlines can separate statements.
- Indentation is used for **blocks** (similar to Python).
- Comments start with `#` and go to the end of the line.

### 3.2 Basic Commands (Illustrative)

> Note: syntax is still a draft; below is a plausible initial version.

#### 3.2.1 Variable and Object Creation

```rosh
create object player
  set name to "Hero"
  set health to 100
  set max health to 100
  set position to { "x": 0, "y": 0 }
end

create number damage as 10
create list enemies
```

#### 3.2.2 Property Access & Assignment

```rosh
set player health to 75
increase player health by 10
decrease player health by 5

get player health into current_health
```

Equivalent stack-style:

```rosh
player "health" get-property   # pushes value
10 add                         # modify on stack
player "health" set-property   # store back
```

#### 3.2.3 Control Flow

```rosh
if player health is below 0 then
  set player health to 0
  say "Player has died."
end

while enemies is not empty do
  take first from enemies into enemy
  attack enemy with player
end
```

Control statements map to underlying opcodes and stack behavior.

#### 3.2.4 Functions / Routines

```rosh
define function heal target by amount
  increase target health by amount
  if target health is above target max health then
    set target health to target max health
  end
end

call heal player by 20
```

Internally, `define function` creates a callable object with access to arguments on the stack or via names.

#### 3.2.5 AI Prompt

```rosh
prompt
  using player, world
  ask "Describe the current scene in one sentence."
  expect text as scene_description
into description

say description
```

---

## 4. Formal Grammar (Draft EBNF)

> This is an initial EBNF-style grammar sketch; actual implementation may diverge for practicality.

```ebnf
program         ::= { statement }

statement       ::= simple_statement NEWLINE
                  | compound_statement

simple_statement ::= assignment
                   | expression_statement
                   | call_statement
                   | import_statement
                   | prompt_statement
                   | create_statement
                   | comment

compound_statement ::= if_block
                     | while_block
                     | function_def
                     | object_def

identifier      ::= LETTER { LETTER | DIGIT | "_" }
number_literal  ::= DIGIT { DIGIT } [ "." DIGIT { DIGIT } ]
string_literal  ::= '"' { CHAR } '"'
boolean_literal ::= "true" | "false"
null_literal    ::= "null"

value_literal   ::= number_literal
                  | string_literal
                  | boolean_literal
                  | null_literal
                  | object_literal
                  | array_literal

object_literal  ::= "{" [ object_pair { "," object_pair } ] "}"
object_pair     ::= string_literal ":" value_literal
array_literal   ::= "[" [ value_literal { "," value_literal } ] "]"

assignment      ::= "set" target "to" expression
                  | "increase" target "by" expression
                  | "decrease" target "by" expression

target          ::= identifier { "." identifier }

expression_statement ::= expression

expression      ::= term { infix_op term }
term            ::= factor { postfix_op }
factor          ::= value_literal
                  | identifier
                  | "(" expression ")"

infix_op        ::= "plus" | "minus" | "times" | "divided by"
postfix_op      ::= "?"  (* example: existence check *)

call_statement  ::= "call" identifier [ argument_list ]
argument_list   ::= argument { "," argument }
argument        ::= identifier
                  | value_literal

import_statement ::= "import" identifier { "." identifier }

if_block        ::= "if" condition "then" NEWLINE
                     INDENT { statement } DEDENT
                     [ "else" NEWLINE
                       INDENT { statement } DEDENT ]
                     "end"

while_block     ::= "while" condition "do" NEWLINE
                     INDENT { statement } DEDENT
                   "end"

function_def    ::= "define" "function" identifier [ parameter_list ] NEWLINE
                     INDENT { statement } DEDENT
                   "end"

parameter_list  ::= identifier { "," identifier }

object_def      ::= "create" "object" identifier NEWLINE
                     INDENT { statement } DEDENT
                   "end"

condition       ::= expression comparison_op expression
                  | expression "is" "true"
                  | expression "is" "false"

comparison_op   ::= "is" "equal to"
                  | "is" "not" "equal to"
                  | "is" "below"
                  | "is" "above"
                  | "is" "at least"
                  | "is" "at most"

prompt_statement ::= "prompt" NEWLINE
                       INDENT prompt_body DEDENT
                     "into" identifier

prompt_body     ::= [ "using" identifier_list NEWLINE ]
                    "ask" string_literal NEWLINE
                    [ "expect" expectation NEWLINE ]

identifier_list ::= identifier { "," identifier }

expectation     ::= "text" "as" identifier
                  | "json" "as" identifier
                  | "list" "of" "json" "as" identifier

comment         ::= "#" { CHAR }
```

This grammar is intentionally high-level and leaves room for natural-language variations that will be implemented as **macro expansions** or additional parsing rules.

---

## 5. Execution Model & Semantics

### 5.1 Overview

A Rosh runtime consists of:

- A **data stack**
- A **call stack**
- A **heap of JSON objects**
- A **dictionary / environment** mapping names to values
- A **module table**
- An **AI adapter** for handling `prompt`

### 5.2 Evaluation Strategy

- Statements are processed top-to-bottom.
- Expressions can be interpreted in **stack style** or **expression style** depending on the parser mode.
- Assignments and property updates directly manipulate JSON objects and property stacks.

### 5.3 Property Stack Semantics (Detailed)

Each object `O` has:

```json
{
  "_meta": {
    "type": "Player",
    "properties": {
      "health": { "stack": [100, 75] },
      "max_health": { "stack": [100] }
    }
  },
  "health": 75,
  "max_health": 100
}
```

Operations:

- `set O.p to v`:
  - Replace the **top of the stack** for `p` with `v`.
- `push O.p v`:
  - Push `v` onto the stack for `p` (shadowing older values).
- `pop O.p`:
  - Pop stack for `p`; if stack becomes empty, delete property or revert to parent.
- Reading `O.p`:
  - Return the top value of the property stack if present.
  - Else check parent objects, if any.
  - Else return `null` or raise error (configurable).

### 5.4 AI Prompt Semantics

`prompt` is desugared to a call to the AI adapter with:

- **Prompt text**: from the `ask` clause.
- **Context**: defined by the `using` clause.
- **Expected structure**: defined by `expect` (text, json, list of json, etc.).

The runtime:

1. Serializes the selected context into JSON.
2. Builds a system/user message specifying the contract.
3. Sends to the configured AI backend.
4. Receives a response and parses it:
   - If `expect text`: take main text answer.
   - If `expect json`: parse as JSON, or attempt to extract JSON from response.
5. Binds the result to the identifier after `into`.

---

## 6. Example Programs

### 6.1 Simple Counter

```rosh
create number counter as 0

define function increment
  increase counter by 1
end

call increment
call increment

say counter   # expected: 2
```

### 6.2 Basic Game Entity

```rosh
create object player
  set name to "Hero"
  set health to 100
  set max health to 100
  set position to { "x": 0, "y": 0 }
end

define function move target by dx dy
  set target position x to target position x plus dx
  set target position y to target position y plus dy
end

call move player by 1 0
```

### 6.3 AI-Driven Dialogue

```rosh
create object player
  set name to "Ari"
  set mood to "nervous"
end

create object npc
  set name to "Gatekeeper"
end

prompt
  using player, npc
  ask "The player approaches the gatekeeper. Write one short line of dialogue for the NPC to say, based on the player's mood."
  expect text as npc_line
into npc_dialogue

say npc_dialogue
```

---

## 7. Implementation Architecture (Python First)

### 7.1 Rationale for Python

Python is chosen as the **reference interpreter** because:

- It has excellent support for JSON, reflection, and dynamic typing.
- Rapid prototyping is easy.
- It’s convenient to integrate with AI APIs (HTTP, SDKs).
- The community and tooling are mature.

The Python interpreter defines the **canonical semantics** of Rosh.

### 7.2 Python Interpreter Architecture

Recommended module layout:

```text
rosh/
  __init__.py
  lexer.py
  parser.py
  ast.py
  vm.py
  values.py
  objects.py
  props.py        # property stack mechanics
  env.py
  stdlib/
    __init__.py
    core.py
    math.py
    ai.py
  backend/
    ai_openai.py
    ai_local.py
```

#### 7.2.1 Lexer

- Tokenizes keywords (`set`, `create`, `define`, `if`, `while`, `prompt`, `using`, `ask`, `expect`, `into`, etc.).
- Handles identifiers, strings, numbers, punctuation, indentation.
- Recognizes natural-language phrases as composite tokens where useful (`is below`, `is above`, `at least`, etc.).

#### 7.2.2 Parser

- Produces an **AST** from tokens according to the grammar.
- Might use a Pratt parser or recursive descent.
- Can implement **macro rules** for spoken-language phrases.

#### 7.2.3 AST

Node types (examples):

- `Program`
- `Block`
- `Assignment`
- `If`
- `While`
- `FunctionDef`
- `Call`
- `Prompt`
- `Literal`
- `Identifier`
- `BinaryOp`
- `PropertyAccess`

#### 7.2.4 VM / Evaluator

Two approaches:

1. **Direct AST interpreter** (simpler initially).
2. **Bytecode compiler + VM** (better for performance and backends).

For v0.1, a **direct AST interpreter** is recommended.

Responsibilities:

- Maintain environment (variables, objects, functions).
- Manage data stack (if used explicitly).
- Enforce property stack semantics.
- Call AI backends for `prompt` nodes.

#### 7.2.5 AI Backend Interface (Python)

Define an abstract interface, for example:

```python
class AIBackend:
    def prompt(self, prompt_text: str, context: dict, expect: str) -> dict | str:
        ...
```

And implementations:

- `OpenAIBackend(AIBackend)`
- `LocalBackend(AIBackend)`

The interpreter uses dependency injection to allow swapping AI backends.

### 7.3 Standard Library (Python Implementation)

Core modules:

- `stdlib.core` – values, printing, basic reflection.
- `stdlib.math` – arithmetic beyond built-ins.
- `stdlib.ai` – higher-level AI helpers (e.g. classify, summarize, plan).

---

## 8. Future Backends

### 8.1 Go Backend

Two options:

1. **Go VM for Rosh bytecode**  
   - Define a portable bytecode format.
   - Implement a VM in Go that executes this bytecode.
   - Pros: Same bytecode runs in Python and Go.
   - Cons: Need bytecode compiler.

2. **Transpile Rosh AST → Go code**  
   - Map Rosh objects to Go structs and maps.
   - Property stacks become slices or custom types.
   - AI calls use HTTP clients in Go.
   - Pros: Native performance, easier debugging in Go.

Initial recommendation: **Option 1** for a faithful implementation, followed by transpiler experiments.

### 8.2 Elixir Backend

Elixir is especially interesting because of its **process model**:

- Map each Rosh object or module to a **GenServer** process.
- Property stacks can be modeled as state within these processes.
- AI prompts can be asynchronous calls (`GenServer.call`) to an AI handler process.

Approach:

- Define a Rosh bytecode interpreter in Elixir, or transpile AST to Elixir modules.
- Provide an AI adapter module in Elixir that mirrors the Python one.

---

## 9. Type System & Schemas (Draft)

Rosh starts with a **soft type system**, but supports optional schemas:

```rosh
define schema Player
  property name as string
  property health as number
  property max health as number
  property position as { x: number, y: number }
end

create object player of type Player
  set name to "Hero"
  set health to 100
  set max health to 100
  set position to { "x": 0, "y": 0 }
end
```

The runtime can:

- Validate objects against schemas on demand.
- Use schemas to improve AI prompts (e.g. telling the model the expected shape of data).

---

## 10. Roadmap & Milestones

### 10.1 Milestone 1: Minimal Python Interpreter

- Implement lexer, parser for:
  - `create object`
  - `set`, `increase`, `decrease`
  - basic `if`, `end`
  - `define function`, `call`
- Implement JSON objects and simple property access (no stacks yet).
- Implement `say` or `print`.
- Run first working scripts.

### 10.2 Milestone 2: Property Stack & Inheritance

- Implement property stack data structures.
- Implement `push`, `pop` semantics for properties.
- Support parent prototypes and property lookup.

### 10.3 Milestone 3: AI Prompt Integration

- Implement `prompt` statement with `using`, `ask`, `expect`, `into`.
- Wire to an AI backend (e.g. via HTTP).

### 10.4 Milestone 4: Standard Library & Modules

- Implement basic stdlib modules.
- Implement `import` semantics.
- Add core game/automation helpers as examples.

### 10.5 Milestone 5: Go Backend Prototype

- Define bytecode format or AST -> Go mapping.
- Implement minimal Go VM or transpiler.
- Run simple Rosh programs via Go.

### 10.6 Milestone 6: Elixir Backend Prototype

- Port VM or transpiler approach to Elixir.
- Demonstrate concurrency via many Rosh objects as processes.

---

## 11. Open Questions & Future Ideas

- How far should natural language flexibility go before it harms predictability?
- Should Rosh support **time-travel debugging** based on property stacks?
- How deeply should the AI integration be able to modify program state autonomously?
- Are there domain-specific “profiles” of Rosh (e.g. Rosh/Game, Rosh/Automation) with pre-built schemas and libraries?

---

## 12. Summary

Rosh is an ambitious but focused attempt to create:

- A **human-friendly**, spoken-language-optimized programming language
- With the **rigor and composability** of stack-based semantics
- Running on a **JSON-native state model**
- With **AI as a first-class primitive**
- Designed to target **Python first**, and later **Go** and **Elixir** for performance and concurrency.

This document should serve as the authoritative starting point for implementing the **first Rosh interpreter in Python**, and as a reference for developing future backends and tools.
