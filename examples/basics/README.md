# Basics - Rosh Interpreter Fundamentals

Learn the core Rosh language features using the interactive interpreter.

## Quick Start

```bash
# Run any example
rosh examples/basics/EXAMPLE_NAME.rosh

# Or use interactive mode
rosh -i examples/basics/EXAMPLE_NAME.rosh
```

## Examples

### **hello.rosh** - Your First Program
```rosh
print "Hello, World!"
```
The classic first program. Demonstrates basic print statements.

---

### **counter.rosh** - Variables and Math
Basic arithmetic and variable manipulation.

**Concepts:**
- Stack operations
- Addition
- Print statements

---

### **conditional.rosh** - Control Flow
If/else statements for decision making.

**Concepts:**
- Conditionals
- Comparisons
- Branching logic

---

### **loop-basic.rosh** - Simple Loops
Your first loop - repeating actions.

**Concepts:**
- While loops
- Loop counters
- Iteration

---

### **loop-factorial.rosh** - Practical Loops
Calculate factorial using loops.

**Concepts:**
- Accumulator pattern
- Mathematical operations in loops
- Loop termination

---

### **math.rosh** - Arithmetic Operations
All the math operations available in Rosh.

**Concepts:**
- Addition, subtraction, multiplication, division
- Modulo
- Stack-based calculations

---

### **stack.rosh** - Stack Basics
Understanding Rosh's stack-based nature.

**Concepts:**
- Push values onto stack
- Pop values from stack
- Stack visualization

---

### **stack-math.rosh** - Stack Arithmetic
Performing calculations using the stack.

**Concepts:**
- Reverse Polish Notation
- Stack-based computation
- Order of operations

---

### **stack-manipulation.rosh** - Advanced Stack
Advanced stack operations.

**Concepts:**
- Swap
- Duplicate
- Stack inspection

---

### **state-dump.rosh** - Debugging
View the complete interpreter state.

**Concepts:**
- State inspection
- Debugging techniques
- Understanding interpreter internals

---

### **player.rosh** - Game Objects
Creating and manipulating game objects.

**Concepts:**
- Object creation
- Properties
- Object state

---

### **save-load.rosh** - Persistence
Save and load game state.

**Concepts:**
- Serialization
- File I/O
- State persistence

---

### **eval-demo.rosh** - Dynamic Code
Execute code dynamically.

**Concepts:**
- Runtime evaluation
- Dynamic programming
- Code as data

---

### **hello-executable.rosh** - Executable Scripts
Make Rosh scripts executable.

**First line:**
```rosh
#!/usr/bin/env rosh
```

**Make executable:**
```bash
chmod +x examples/basics/hello-executable.rosh
./examples/basics/hello-executable.rosh
```

---

### **hello-robot.rosh** - Fun Output
A more creative hello world!

---

## Learning Path

1. **hello.rosh** - Start here!
2. **counter.rosh** - Learn variables
3. **conditional.rosh** - Add logic
4. **loop-basic.rosh** - Learn loops
5. **math.rosh** - Explore operations
6. **stack.rosh** - Understand the stack
7. **player.rosh** - Create game objects
8. **save-load.rosh** - Add persistence

## Interactive Mode

The Rosh REPL (Read-Eval-Print Loop) lets you experiment:

```bash
rosh  # Start interactive mode

> print "Hello!"
Hello!

> 5 plus 3 print
8
```

## Next Steps

Once you've mastered the basics, explore:
- **../advanced/** - Advanced language features
- **../games/** - Browser games with Phaser
- **../mud/** - Text adventure games
