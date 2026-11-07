# What a line of Rosh means

This page and `cases.json` beside it are the definition. Any engine that passes the cases runs Rosh, whatever it is
written in. If this page and a case disagree, that's a bug in one of them; if an engine and a case disagree, the bug
is in the engine, or the case is wrong and gets changed on purpose.

## The rule everything else follows

**The same line gives the same result everywhere, or a clear refusal that names the line. It never quietly does
something else.**

## Two layers

| | Plain English | Rosh |
|---|---|---|
| Example | `make the ball a bit bigger` | `set ball.width to 1.25` |
| Job | Guess what a person means | Say exactly what happens |
| When unsure | Asks, or shows its best guess as Rosh | Refuses |
| Where it lives | On top, optional, can improve freely | Fixed by this page |

Plain English must turn into Rosh before anything runs. It must never take a line that's already valid Rosh and read
it as something else: `add 1 to items` is a list statement, not "make one thing called items" (case `list-add-each`).

## Statements

| Statement | Means | Refuses when |
|---|---|---|
| `create object m` | Makes `m` | |
| `create scene s` | Makes a scene, not an object | |
| `destroy m` | Removes `m` | |
| `set m.x to 2` | Sets a property | Nothing follows `to` |
| `set n to 4` | Sets a variable | Nothing follows `to` |
| `set a.parent to object b` | A checked reference, stored as `b`'s name | `b` isn't an object. Later: destroying `b`, setting it to nothing or forgetting it while `a.parent` points at it |
| `set m.x to m.x + 3` | Values may be worked out from numbers, properties and variables | |
| `print "n is {n}"` | Writes text; `{n}` is replaced by its value | |
| `say hello` | Says it to whoever is there | |
| `if` / `else if` / `else` / `end` | Runs one branch. Compares with `==` `!=` `>` `<` `>=` `<=` | Any other operator; no `end` |
| `repeat 3` ... `end` | Runs the body 3 times | No `end` |
| `repeat 3 as i` ... `end` | As above, with `i` counting **from 1** | No `end` |
| `define up` ... `end`, `do up` | Stores the body from that line on; `do` runs it. A later `define` replaces it from there on | `do` above the `define`; a procedure calling itself |
| `when e` ... `end` | Stores the body; it waits for `e` | No `end` |
| `on e <action>` | One-line form of `when` | |
| `event e a b` | Names an event's values | |
| `send e a=1` | Fires `e`; `a` is readable inside the handler | A value with no name: `send e 8` |
| `add 1 to items` | Adds to a list, starting it if needed | The target exists and isn't a list; the item is itself a list |
| `remove 1 from items` | Removes the first match; no match changes nothing | |
| `for each v in items` ... `end` | Runs the body per item | The target isn't a list |

Any other first word on a line is refused. So is a stray `else` or `end`, text over 100,000 characters, a number too
big to hold (beyond about 1e308) and more than 64 values in one expression, because a value can grow by itself in a loop. A list holds up to 10,000 items of
up to 1,000 characters each, and a room's code can run 200 `if`, `repeat`, `for each`, `send` or `do` units as it loads.

## A room file

A room file is the same language, with one difference: **a mistake costs only the line or block it's in**, and the rest
of the room still loads, because a room is a document someone is editing. A script file is refused as a whole.

- A block (`if`, `repeat`, `define`, `when`, `for each`) runs as one thing. If any line in it is bad, none of it runs.
- Every refused line is reported with its line number in the file.
- A line that's accepted but will visibly do nothing gets a warning, such as a handler nothing fires.

## Decided

1. **Clicks reach a room.** `when click_<thing>` runs when someone clicks that thing, for everyone, with no more than a
   visitor's rights even if the owner clicked: anyone may have written the rule. The room's history records what fired,
   who fired it, and what changed or why it failed. Keys, frames and timers don't reach a room yet, and the editor says so.
2. **Values can be typed in a live room.** What a visitor sets is theirs; a guest's is open again once they've gone; the
   room's own are open to all, as with things. A room holds up to 100, up to 1 MB in all. They last as long as the room
   does. A word close to a thing's name is asked about, not kept.
3. **The first value fixes the kind of thing a name holds:** a number, text, true or false, a list, or a thing.
   `set x to nothing` frees the name. Text times a number, dividing by zero, `if nosuch > 1`, comparing a number's order with text, and
   `repeat 20000` are all errors. `==` and `!=` always have an answer, and inside a handler or a listener's condition, a value not set yet is quietly false, since it may be waiting.

4. **A failed line changes nothing it shouldn't.** Parameters, loop names and event values go back on every way out, and
   a name they hide isn't touched. In a live room, a refused command leaves the room as it was, including what can't be seen.

## Not settled yet

These are listed so nobody mistakes them for what the engines do today.

5. **New properties and permissions.** Giving a thing that exists a new property is allowed: it's how all Rosh is
   written, and `create` can't carry properties, so fixing them at creation would need new syntax. Who may do it is a
   permissions question: in a shared room you can't change someone else's thing. Whether properties should ever be fixed
   at creation for security is a design decision not yet taken.
6. **Does `set nosuch.x to 1` make `nosuch`?** Scripts and room files say yes; a live room refuses. Refusing catches
   typos; 22 lines in 10 existing sources rely on it.

## Known limits of this page

- In a browser, `add you to visitors` keeps a room list (`look room`), and `print "{n}"` doesn't see the room's values.
  Both are in the plain-English layer on top, not the language.
- It covers the core statements, not widgets, sprites, sounds, animation or connections: for those the cases only
  check that they're accepted, not what they do.
- A room's limit of 200 running blocks at load counts the blocks written, not those reached through a loop or procedure;
  the step limit still stops any of them running too long.
- `bad-unknown-name` fails today by design of the question above, until it's decided.
- Passing the cases shows an engine agrees on these examples. It doesn't prove it agrees everywhere; that's what the
  generated test programs are for.
