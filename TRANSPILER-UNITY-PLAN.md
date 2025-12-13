# Unity C# Transpiler Architecture Plan

**Status:** Design Phase (v0.0.7+)
**Priority:** 1 (Critical for enterprise VR market)
**Target:** Q2-Q3 2026
**Owner:** TBD (Compiler Engineer needed)

---

## Executive Summary

The Unity C# transpiler will convert Rosh code into idiomatic Unity C# scripts that integrate seamlessly with Unity projects. This enables VR developers to voice-script game logic while immersed in VR, then compile to production-ready C# code.

**Key Design Principles:**
1. **Readable Output:** Generated C# should look hand-written
2. **Unity Best Practices:** Follow Unity coding conventions and patterns
3. **No Runtime Dependency:** Pure C# output, no Rosh interpreter needed
4. **Incremental Transpilation:** Support partial script updates
5. **Type Safety:** Leverage Unity's type system

---

## 1. Architecture Overview

```
┌─────────────────┐
│  Rosh Source    │  (voice-dictated .rosh files)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Rosh Parser    │  (existing: lexer.py → parser.py → AST)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Transpiler Core │  (NEW: transpiler/unity_csharp.py)
└────────┬────────┘
         │
         ├─→ AST Visitor Pattern
         ├─→ Type Inference Engine
         ├─→ Unity API Mapper
         ├─→ C# Code Generator
         │
         ▼
┌─────────────────┐
│  Unity C# Code  │  (output: Assets/Scripts/*.cs)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Unity Compiler │  (built-in: produces .dll for runtime)
└─────────────────┘
```

---

## 2. Rosh → Unity Mapping

### 2.1 Objects → MonoBehaviour Classes

**Rosh:**
```rosh
create object player
    set name to "Hero"
    set health to 100
    set position to [0, 5, 0]
end
```

**Unity C#:**
```csharp
using UnityEngine;

public class Player : MonoBehaviour
{
    public string name = "Hero";
    public int health = 100;
    public Vector3 position = new Vector3(0, 5, 0);

    void Start()
    {
        transform.position = position;
    }
}
```

**Mapping Rules:**
- Rosh `object` → Unity `MonoBehaviour` class
- Object name capitalized (player → Player)
- Properties become public fields (Unity Inspector editable)
- Position/rotation auto-sync with Transform component

---

### 2.2 Functions → Methods

**Rosh:**
```rosh
define function take_damage amount
    set player.health to player.health minus amount
    if player.health is below 0 then
        call die
    end
end

define function die
    print "Game Over"
    set player.active to false
end
```

**Unity C#:**
```csharp
public void TakeDamage(int amount)
{
    health -= amount;
    if (health < 0)
    {
        Die();
    }
}

public void Die()
{
    Debug.Log("Game Over");
    gameObject.SetActive(false);
}
```

**Mapping Rules:**
- Rosh `define function` → C# `public void` method
- Snake_case → PascalCase naming
- Rosh `print` → C# `Debug.Log()`
- Rosh `active` property → Unity `gameObject.SetActive()`

---

### 2.3 Events → Unity Event System

**Rosh:**
```rosh
when player.health is below 20 then
    play sound "warning_beep"
    set ui_health_color to "red"
end
```

**Unity C# (Option A: Update Loop):**
```csharp
void Update()
{
    if (health < 20)
    {
        AudioSource.PlayClipAtPoint(warningBeep, transform.position);
        uiHealthColor = Color.red;
    }
}
```

**Unity C# (Option B: Property Observer):**
```csharp
private int _health = 100;
public int health
{
    get { return _health; }
    set
    {
        _health = value;
        if (_health < 20)
        {
            OnHealthCritical();
        }
    }
}

void OnHealthCritical()
{
    AudioSource.PlayClipAtPoint(warningBeep, transform.position);
    uiHealthColor = Color.red;
}
```

**Design Decision:** Use Option B (property observers) for performance.

---

### 2.4 Loops → C# Control Flow

**Rosh:**
```rosh
for i in 1 to 5 then
    print i
end

for enemy in all enemies then
    call enemy.attack player
end
```

**Unity C#:**
```csharp
// Range loop
for (int i = 1; i <= 5; i++)
{
    Debug.Log(i);
}

// Collection loop
foreach (Enemy enemy in enemies)
{
    enemy.Attack(player);
}
```

**Mapping Rules:**
- `for i in X to Y` → C# `for (int i = X; i <= Y; i++)`
- `for item in collection` → C# `foreach (var item in collection)`
- `for obj in all TypeName` → Find all GameObjects with TypeName component

---

### 2.5 Vectors and Unity Math

**Rosh:**
```rosh
set position to [10, 0, 5]
set direction to [0, 0, 1]
set new_position to position plus direction times 5
```

**Unity C#:**
```csharp
Vector3 position = new Vector3(10, 0, 5);
Vector3 direction = new Vector3(0, 0, 1);
Vector3 newPosition = position + direction * 5;
```

**Mapping Rules:**
- Rosh `[x, y, z]` → Unity `Vector3(x, y, z)`
- Rosh `plus` → C# `+`
- Rosh `times` → C# `*`
- Auto-detect vector operations and use Unity's Vector3 math

---

### 2.6 Unity-Specific APIs

**Rosh Extensions (to be designed in v0.0.8+):**

```rosh
# Physics
set hit to raycast from player.position direction [0, 0, 1] distance 10
if hit.collider is not null then
    print hit.point
end

# Animation
play animation "walk" on player
set animation_speed to 1.5

# Coroutines (for time-based actions)
start coroutine wait 2 seconds then
    print "Delayed message"
end
```

**Unity C# Output:**
```csharp
// Raycast
RaycastHit hit;
if (Physics.Raycast(player.position, Vector3.forward, out hit, 10f))
{
    Debug.Log(hit.point);
}

// Animation
GetComponent<Animator>().Play("walk");
GetComponent<Animator>().speed = 1.5f;

// Coroutines
IEnumerator DelayedAction()
{
    yield return new WaitForSeconds(2f);
    Debug.Log("Delayed message");
}
StartCoroutine(DelayedAction());
```

---

## 3. Transpiler Implementation

### 3.1 File Structure

```
rosh-lang/
├── src/
│   └── rosh/
│       └── transpiler/
│           ├── __init__.py
│           ├── base.py           # Base transpiler class
│           ├── unity_csharp.py   # Unity C# transpiler
│           ├── javascript.py     # WebXR transpiler (future)
│           ├── gdscript.py       # Godot transpiler (future)
│           └── lua.py            # Roblox transpiler (future)
├── tests/
│   └── test_transpiler/
│       ├── test_unity_basic.py
│       ├── test_unity_objects.py
│       ├── test_unity_events.py
│       └── test_unity_integration.py
└── examples/
    └── transpiler/
        ├── simple_game.rosh
        └── simple_game.cs  # Expected output
```

### 3.2 Core Classes

#### base.py - Abstract Base Transpiler

```python
from abc import ABC, abstractmethod
from typing import List
from rosh.ast_nodes import ASTNode

class Transpiler(ABC):
    """Base class for all transpilers"""

    def __init__(self, ast: List[ASTNode]):
        self.ast = ast
        self.output_lines: List[str] = []
        self.indent_level = 0

    @abstractmethod
    def transpile(self) -> str:
        """Convert AST to target language"""
        pass

    def indent(self) -> str:
        """Get current indentation string"""
        return "    " * self.indent_level

    def emit(self, line: str):
        """Emit a line of code with current indentation"""
        self.output_lines.append(self.indent() + line)
```

#### unity_csharp.py - Unity C# Transpiler

```python
from typing import List, Dict, Any
from rosh.ast_nodes import *
from rosh.transpiler.base import Transpiler

class UnityCSharpTranspiler(Transpiler):
    """Transpile Rosh AST to Unity C# code"""

    def __init__(self, ast: List[ASTNode]):
        super().__init__(ast)
        self.classes: Dict[str, List[ASTNode]] = {}
        self.current_class = None
        self.type_hints: Dict[str, str] = {}

    def transpile(self) -> str:
        """Main transpilation entry point"""
        # Phase 1: Analyze AST and group by classes
        self._analyze_ast()

        # Phase 2: Generate C# code
        self._generate_usings()
        self._generate_classes()

        return "\n".join(self.output_lines)

    def _analyze_ast(self):
        """First pass: identify objects and group related code"""
        for node in self.ast:
            if isinstance(node, CreateObject):
                self._register_class(node)
            elif isinstance(node, DefineFunction):
                self._register_method(node)

    def _register_class(self, node: CreateObject):
        """Register a new MonoBehaviour class"""
        class_name = self._to_pascal_case(node.name)
        if class_name not in self.classes:
            self.classes[class_name] = []
        self.classes[class_name].append(node)

    def _generate_usings(self):
        """Generate using statements"""
        self.emit("using UnityEngine;")
        self.emit("using System.Collections;")
        self.emit("using System.Collections.Generic;")
        self.emit("")

    def _generate_classes(self):
        """Generate all MonoBehaviour classes"""
        for class_name, nodes in self.classes.items():
            self._generate_class(class_name, nodes)

    def _generate_class(self, class_name: str, nodes: List[ASTNode]):
        """Generate a single MonoBehaviour class"""
        self.emit(f"public class {class_name} : MonoBehaviour")
        self.emit("{")
        self.indent_level += 1

        # Generate fields
        for node in nodes:
            if isinstance(node, CreateObject):
                self._generate_fields(node)

        # Generate methods
        for node in nodes:
            if isinstance(node, DefineFunction):
                self._generate_method(node)

        self.indent_level -= 1
        self.emit("}")
        self.emit("")

    def _generate_fields(self, node: CreateObject):
        """Generate class fields from object properties"""
        for prop_name, prop_value in node.properties.items():
            csharp_type = self._infer_type(prop_value)
            csharp_name = self._to_camel_case(prop_name)
            csharp_value = self._transpile_expression(prop_value)
            self.emit(f"public {csharp_type} {csharp_name} = {csharp_value};")

    def _generate_method(self, node: DefineFunction):
        """Generate a C# method from Rosh function"""
        method_name = self._to_pascal_case(node.name)
        params = ", ".join(
            f"{self._infer_param_type(p)} {p}"
            for p in node.parameters
        )

        self.emit(f"public void {method_name}({params})")
        self.emit("{")
        self.indent_level += 1

        for statement in node.body:
            self._transpile_statement(statement)

        self.indent_level -= 1
        self.emit("}")
        self.emit("")

    def _transpile_statement(self, node: ASTNode):
        """Transpile a single statement"""
        if isinstance(node, SetVariable):
            self._transpile_set(node)
        elif isinstance(node, IfStatement):
            self._transpile_if(node)
        elif isinstance(node, ForLoop):
            self._transpile_for(node)
        elif isinstance(node, Print):
            self._transpile_print(node)
        # ... more statement types

    def _transpile_set(self, node: SetVariable):
        """Transpile: set x to y"""
        var_name = self._to_camel_case(node.name)
        value = self._transpile_expression(node.value)
        self.emit(f"{var_name} = {value};")

    def _transpile_if(self, node: IfStatement):
        """Transpile: if condition then ... end"""
        condition = self._transpile_expression(node.condition)
        self.emit(f"if ({condition})")
        self.emit("{")
        self.indent_level += 1

        for stmt in node.then_block:
            self._transpile_statement(stmt)

        self.indent_level -= 1
        self.emit("}")

        if node.else_block:
            self.emit("else")
            self.emit("{")
            self.indent_level += 1
            for stmt in node.else_block:
                self._transpile_statement(stmt)
            self.indent_level -= 1
            self.emit("}")

    def _transpile_expression(self, node: ASTNode) -> str:
        """Transpile an expression to C# code"""
        if isinstance(node, Number):
            return str(node.value)
        elif isinstance(node, String):
            return f'"{node.value}"'
        elif isinstance(node, BinaryOp):
            return self._transpile_binary_op(node)
        elif isinstance(node, ListLiteral):
            return self._transpile_list(node)
        # ... more expression types
        return "null"

    def _transpile_binary_op(self, node: BinaryOp) -> str:
        """Transpile binary operations"""
        left = self._transpile_expression(node.left)
        right = self._transpile_expression(node.right)

        # Map Rosh operators to C#
        op_map = {
            'plus': '+',
            'minus': '-',
            'times': '*',
            'divided by': '/',
            'is equal to': '==',
            'is above': '>',
            'is below': '<',
            'and': '&&',
            'or': '||',
        }

        csharp_op = op_map.get(node.operator, node.operator)
        return f"({left} {csharp_op} {right})"

    def _infer_type(self, node: ASTNode) -> str:
        """Infer C# type from Rosh value"""
        if isinstance(node, Number):
            return "int" if isinstance(node.value, int) else "float"
        elif isinstance(node, String):
            return "string"
        elif isinstance(node, ListLiteral):
            if len(node.elements) == 3:
                # Assume [x, y, z] is a Vector3
                return "Vector3"
            return "List<object>"
        return "object"

    def _to_pascal_case(self, name: str) -> str:
        """Convert snake_case to PascalCase"""
        return "".join(word.capitalize() for word in name.split("_"))

    def _to_camel_case(self, name: str) -> str:
        """Convert snake_case to camelCase"""
        words = name.split("_")
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])
```

---

## 4. Type Inference System

### 4.1 Challenge

Rosh is dynamically typed, but C# is statically typed. We need to infer types.

### 4.2 Inference Strategy

**1. Literal-based inference:**
```rosh
set x to 42        # → int x = 42;
set name to "Bob"  # → string name = "Bob";
set pos to [0,0,0] # → Vector3 pos = new Vector3(0,0,0);
```

**2. Operation-based inference:**
```rosh
set result to x plus y  # If x and y are int, result is int
set dist to length of vector  # → float dist = vector.magnitude;
```

**3. Unity API hints:**
```rosh
set hit to raycast ...  # → RaycastHit hit;
play animation "walk"   # Implies Animator component exists
```

**4. Type annotations (optional in Rosh v0.0.7+):**
```rosh
create number:int score to 0
create object:Enemy goblin
```

### 4.3 Type Inference Implementation

```python
class TypeInferenceEngine:
    def __init__(self):
        self.type_db: Dict[str, str] = {}  # var_name → C# type

    def infer_type(self, node: ASTNode, context: Dict[str, Any]) -> str:
        """Infer C# type from AST node"""

        if isinstance(node, Number):
            return "int" if isinstance(node.value, int) else "float"

        elif isinstance(node, String):
            return "string"

        elif isinstance(node, ListLiteral):
            if len(node.elements) == 3:
                # Check if all elements are numbers → Vector3
                if all(isinstance(e, Number) for e in node.elements):
                    return "Vector3"
            # Generic list
            element_types = [self.infer_type(e, context) for e in node.elements]
            common_type = self._find_common_type(element_types)
            return f"List<{common_type}>"

        elif isinstance(node, BinaryOp):
            left_type = self.infer_type(node.left, context)
            right_type = self.infer_type(node.right, context)
            return self._infer_binary_result_type(left_type, right_type, node.operator)

        return "object"  # Fallback

    def _infer_binary_result_type(self, left: str, right: str, op: str) -> str:
        """Infer result type of binary operation"""
        if op in ['plus', 'minus', 'times', 'divided by']:
            if left == right:
                return left
            if 'float' in [left, right]:
                return 'float'
            return 'int'

        elif op in ['is equal to', 'is above', 'is below', 'and', 'or']:
            return 'bool'

        return 'object'
```

---

## 5. Unity API Integration

### 5.1 Component Access Patterns

**Rosh:**
```rosh
# Implicit component access
set player.position to [10, 0, 5]
play animation "walk" on player
play sound "coin_pickup"
```

**Unity C#:**
```csharp
// Explicit GetComponent calls
transform.position = new Vector3(10, 0, 5);
GetComponent<Animator>().Play("walk");
AudioSource.PlayClipAtPoint(coinPickup, transform.position);
```

**Transpiler Strategy:**
- Maintain a map of common Unity components
- Auto-generate GetComponent<T>() calls
- Cache component references in Start() for performance

### 5.2 Unity Component Map

```python
UNITY_COMPONENT_MAP = {
    'position': 'transform.position',
    'rotation': 'transform.rotation',
    'scale': 'transform.localScale',
    'active': 'gameObject.SetActive',
    'tag': 'gameObject.tag',
    'layer': 'gameObject.layer',
    'velocity': 'GetComponent<Rigidbody>().velocity',
    'angularVelocity': 'GetComponent<Rigidbody>().angularVelocity',
}

UNITY_METHOD_MAP = {
    'play animation': 'GetComponent<Animator>().Play',
    'play sound': 'AudioSource.PlayClipAtPoint',
    'instantiate': 'Instantiate',
    'destroy': 'Destroy',
    'find object': 'GameObject.Find',
}
```

### 5.3 Generated Component Cache

For performance, cache component references:

```csharp
// Generated in Start() method
private Animator _animator;
private Rigidbody _rigidbody;
private AudioSource _audioSource;

void Start()
{
    _animator = GetComponent<Animator>();
    _rigidbody = GetComponent<Rigidbody>();
    _audioSource = GetComponent<AudioSource>();
}
```

---

## 6. Event System Transpilation

### 6.1 Rosh Event Syntax (v0.0.7)

```rosh
when player.health is below 20 then
    call show_warning
end

when player collides with enemy then
    call take_damage 10
end

when button "fire" is pressed then
    call shoot
end
```

### 6.2 Unity C# Event Patterns

**Pattern 1: Update() Polling**
```csharp
void Update()
{
    if (health < 20)
    {
        ShowWarning();
    }

    if (Input.GetButtonDown("fire"))
    {
        Shoot();
    }
}
```

**Pattern 2: OnTriggerEnter (Collision)**
```csharp
void OnTriggerEnter(Collider other)
{
    if (other.CompareTag("Enemy"))
    {
        TakeDamage(10);
    }
}
```

**Pattern 3: Property Observers**
```csharp
private int _health;
public int health
{
    get => _health;
    set
    {
        _health = value;
        if (_health < 20) ShowWarning();
    }
}
```

### 6.3 Transpilation Strategy

```python
def _transpile_when_statement(self, node: WhenStatement):
    """Transpile Rosh 'when' to appropriate Unity pattern"""

    # Analyze condition to determine event type
    if self._is_collision_event(node.condition):
        self._generate_collision_handler(node)

    elif self._is_input_event(node.condition):
        self._generate_input_handler(node)

    elif self._is_property_check(node.condition):
        self._generate_property_observer(node)

    else:
        # Fallback: polling in Update()
        self._generate_update_polling(node)
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

Test individual transpilation functions:

```python
def test_transpile_simple_object():
    rosh_code = """
    create object player
        set health to 100
    end
    """

    expected_csharp = """
    using UnityEngine;

    public class Player : MonoBehaviour
    {
        public int health = 100;
    }
    """

    ast = parse_rosh(rosh_code)
    transpiler = UnityCSharpTranspiler(ast)
    output = transpiler.transpile()

    assert normalize_whitespace(output) == normalize_whitespace(expected_csharp)
```

### 7.2 Integration Tests

Test full Rosh scripts → compilable C#:

```python
def test_transpile_simple_game():
    rosh_file = "examples/simple_game.rosh"
    expected_cs = "examples/simple_game.cs"

    with open(rosh_file) as f:
        rosh_code = f.read()

    ast = parse_rosh(rosh_code)
    transpiler = UnityCSharpTranspiler(ast)
    output = transpiler.transpile()

    # Verify output compiles in Unity
    assert compiles_in_unity(output)

    # Optionally check against reference
    with open(expected_cs) as f:
        expected = f.read()
    assert normalize_code(output) == normalize_code(expected)
```

### 7.3 Unity Compilation Test

```python
def compiles_in_unity(csharp_code: str) -> bool:
    """Test if generated C# actually compiles in Unity"""
    import subprocess
    import tempfile

    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.cs', delete=False) as f:
        f.write(csharp_code.encode('utf-8'))
        temp_path = f.name

    # Use Unity's C# compiler (csc.exe or mcs)
    # This requires Unity installed on CI system
    result = subprocess.run(
        ['csc', '/target:library', '/r:UnityEngine.dll', temp_path],
        capture_output=True
    )

    return result.returncode == 0
```

---

## 8. Implementation Phases

### Phase 1: MVP (Milestone 10 - Q2 2026)

**Goal:** Basic transpilation for simple games

**Features:**
- Objects → MonoBehaviour classes
- Functions → Methods
- Variables and arithmetic
- If/else conditionals
- For loops (range only)
- Print → Debug.Log

**Deliverable:** Transpile dungeon-crawler.rosh to Unity C#

**Estimated Effort:** 6-8 weeks

---

### Phase 2: VR Support (Milestone 11 - Q3 2026)

**Goal:** Unity VR API integration

**Features:**
- XR input handling (controllers, hands)
- XR rig integration (player position/rotation)
- Teleportation and locomotion
- Grabbable objects
- UI in world space

**Deliverable:** Voice-script a simple VR interaction demo

**Estimated Effort:** 4-6 weeks

---

### Phase 3: Advanced Features (Milestone 12 - Q4 2026)

**Goal:** Production-ready transpiler

**Features:**
- Event system (when/trigger) → Unity callbacks
- Coroutines for time-based actions
- Physics (raycasts, collisions)
- Animation state machines
- Audio playback
- Particle effects

**Deliverable:** Museum VR exhibit demo

**Estimated Effort:** 8-10 weeks

---

### Phase 4: Optimization (Milestone 13 - Q1 2027)

**Goal:** Performance and polish

**Features:**
- Type inference improvements
- Component caching
- Code minimization
- Unity best practices (object pooling, etc.)
- Documentation generation
- IDE integration (syntax highlighting for .cs output)

**Deliverable:** Enterprise-ready transpiler

**Estimated Effort:** 4-6 weeks

---

## 9. Example: Full Transpilation

### Input: dungeon-crawler.rosh (simplified)

```rosh
# Player object
create object player
    set health to 100
    set max_health to 100
    set position to [0, 0, 0]
end

# Enemy object
create object goblin
    set health to 30
    set damage to 10
    set position to [5, 0, 5]
end

# Player take damage
define function take_damage amount
    set player.health to player.health minus amount
    if player.health is below 0 then
        call die
    end
end

# Player death
define function die
    print "Game Over"
    set player.active to false
end

# Combat event
when player collides with goblin then
    call take_damage goblin.damage
end
```

### Output: Generated Unity C#

```csharp
using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class Player : MonoBehaviour
{
    public int health = 100;
    public int maxHealth = 100;
    public Vector3 position = new Vector3(0, 0, 0);

    void Start()
    {
        transform.position = position;
    }

    public void TakeDamage(int amount)
    {
        health -= amount;
        if (health < 0)
        {
            Die();
        }
    }

    public void Die()
    {
        Debug.Log("Game Over");
        gameObject.SetActive(false);
    }

    void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Goblin"))
        {
            Goblin goblin = other.GetComponent<Goblin>();
            TakeDamage(goblin.damage);
        }
    }
}

public class Goblin : MonoBehaviour
{
    public int health = 30;
    public int damage = 10;
    public Vector3 position = new Vector3(5, 0, 5);

    void Start()
    {
        transform.position = position;
        gameObject.tag = "Goblin";
    }
}
```

---

## 10. Challenges and Solutions

### Challenge 1: Stateful vs. Stateless

**Problem:** Rosh interpreter maintains global state. Unity MonoBehaviours are instance-based.

**Solution:**
- Each Rosh `object` becomes a separate MonoBehaviour class
- Global variables become static fields on a GameManager class
- Instance variables become MonoBehaviour fields

### Challenge 2: Stack-Based Execution

**Problem:** Rosh uses a stack for expression results. C# doesn't.

**Solution:**
- Inline stack operations as C# expressions
- `get player.health; print stack` → `Debug.Log(health);`

### Challenge 3: Dynamic Typing

**Problem:** Rosh is dynamically typed, Unity C# is static.

**Solution:**
- Type inference engine
- Optional type annotations in Rosh
- Fallback to `object` type when uncertain

### Challenge 4: Unity Editor Integration

**Problem:** Generated code needs to work in Unity Editor.

**Solution:**
- Use `[SerializeField]` attributes for Inspector exposure
- Generate MonoBehaviour lifecycle methods (Awake, Start, Update)
- Support Unity's component model (GetComponent, etc.)

### Challenge 5: Multi-File Output

**Problem:** Large Rosh files should split into multiple C# files.

**Solution:**
- One C# file per Rosh `object` definition
- Shared utilities in separate `RoshRuntime.cs` file
- Namespace organization

---

## 11. CLI Interface

### 11.1 Basic Usage

```bash
# Transpile single file
rosh transpile dungeon-crawler.rosh --target unity --output Assets/Scripts/

# Transpile entire project
rosh transpile examples/*.rosh --target unity --output Assets/Scripts/

# Watch mode (auto-transpile on save)
rosh transpile dungeon-crawler.rosh --target unity --watch
```

### 11.2 Options

```
--target         Target language: unity, javascript, gdscript, lua
--output         Output directory (default: ./transpiled/)
--watch          Auto-transpile on file changes
--namespace      C# namespace (default: RoshGenerated)
--optimize       Enable optimizations
--verify         Compile output to verify syntax
--verbose        Show detailed transpilation steps
```

### 11.3 Implementation

```python
# cli.py
import argparse
from rosh.transpiler.unity_csharp import UnityCSharpTranspiler

def transpile_command(args):
    """Handle 'rosh transpile' command"""

    # Read input
    with open(args.input_file) as f:
        rosh_code = f.read()

    # Parse
    from rosh.lexer import Lexer
    from rosh.parser import Parser

    lexer = Lexer(rosh_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    # Transpile
    if args.target == 'unity':
        transpiler = UnityCSharpTranspiler(ast)
    elif args.target == 'javascript':
        transpiler = JavaScriptTranspiler(ast)
    # ... other targets

    output = transpiler.transpile()

    # Write output
    output_path = args.output or f"{args.input_file}.cs"
    with open(output_path, 'w') as f:
        f.write(output)

    print(f"✓ Transpiled {args.input_file} → {output_path}")
```

---

## 12. Future Enhancements

### 12.1 Bidirectional Sync (v2.0+)

Allow editing generated C# and syncing back to Rosh:

```bash
rosh sync Assets/Scripts/Player.cs → player.rosh
```

### 12.2 Debugging Support

Generate source maps for Unity debugger:

```csharp
// player.rosh:15 → Player.cs:42
#line 15 "player.rosh"
health -= amount;
```

### 12.3 Asset References

Support Unity asset references in Rosh:

```rosh
create object player
    set sprite to asset "player_sprite.png"
    set sound to asset "jump.wav"
end
```

Transpiles to:

```csharp
[SerializeField] private Sprite sprite;
[SerializeField] private AudioClip sound;
```

---

## 13. Success Metrics

**Transpiler is considered production-ready when:**

1. ✅ Dungeon-crawler demo transpiles to compilable Unity C#
2. ✅ Generated code passes Unity's own code analyzer (no warnings)
3. ✅ Performance: transpiled code runs at 60 FPS with 100+ objects
4. ✅ 95%+ unit test coverage on transpiler code
5. ✅ At least 1 enterprise client ships a VR project using Rosh → Unity workflow
6. ✅ Documentation: Full API reference and tutorial series

---

## 14. Resources Required

**Personnel:**
- 1 Senior Compiler Engineer (6 months, full-time)
- 1 Unity Developer (3 months, part-time for testing/integration)

**Budget:**
- Salaries: ~$80K (contractor rates)
- Unity Pro licenses: $2K/year
- Testing infrastructure: $5K

**Total: ~$87K for Phase 1-3**

---

## 15. Risk Mitigation

**Risk 1: Unity API changes**
- Mitigation: Target LTS versions of Unity (2022 LTS, 2023 LTS)
- Quarterly reviews of Unity API updates

**Risk 2: Type inference failures**
- Mitigation: Allow manual type annotations in Rosh
- Comprehensive test suite for edge cases

**Risk 3: Performance of generated code**
- Mitigation: Benchmarking suite
- Optimize common patterns (object pooling, caching)

**Risk 4: Developer adoption**
- Mitigation: Excellent documentation
- Side-by-side examples (Rosh vs. C#)
- Video tutorials

---

## 16. Timeline Summary

| Phase | Milestone | Duration | Completion Target |
|-------|-----------|----------|-------------------|
| 1. MVP | M10 | 6-8 weeks | Q2 2026 |
| 2. VR Support | M11 | 4-6 weeks | Q3 2026 |
| 3. Advanced | M12 | 8-10 weeks | Q4 2026 |
| 4. Optimization | M13 | 4-6 weeks | Q1 2027 |

**Total: 22-30 weeks (~6 months)**

---

## 17. Next Steps

**Immediate (Q1 2027):**
1. Create `transpiler/` directory structure
2. Implement base transpiler class
3. Write 10 unit tests for simple transpilations
4. Transpile "Hello World" Rosh → Unity C#

**Near-term (Q2 2026):**
1. Implement type inference engine
2. Complete object → MonoBehaviour transpilation
3. Transpile dungeon-crawler.rosh demo
4. Hire compiler engineer

**Long-term (Q3-Q4 2026):**
1. VR API integration
2. Event system transpilation
3. Enterprise pilot program
4. Production release

---

*Last Updated: December 13, 2025*
*Rosh Language Project - TRANSPILER-UNITY-PLAN.md*
