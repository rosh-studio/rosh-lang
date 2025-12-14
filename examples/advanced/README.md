# Advanced - Advanced Language Features

Master advanced Rosh concepts for complex programs.

## Quick Start

```bash
# Run any advanced example
rosh examples/advanced/EXAMPLE_NAME.rosh
```

## Examples

### **inheritance-single.rosh** - Single Inheritance
Objects inheriting from one parent.

**Concepts:**
- Parent-child relationships
- Property inheritance
- Overriding properties

**Example:**
```rosh
create object warrior from character
    set strength to 10
end
```

---

### **inheritance-multiple.rosh** - Multiple Inheritance
Objects inheriting from multiple parents.

**Concepts:**
- Multiple parent types
- Property merging
- Inheritance order

---

### **inheritance-complete.rosh** - Complete Inheritance System
Comprehensive inheritance examples.

**Concepts:**
- Deep inheritance chains
- Property resolution
- Inheritance best practices

---

### **for-loops.rosh** - For Loops
Iterate over collections and ranges.

**Concepts:**
- For loop syntax
- Range iteration
- Collection iteration

---

### **property-stacks.rosh** - Property Manipulation
Advanced property operations.

**Concepts:**
- Property stacks
- Dynamic properties
- Property lookup

---

### **stack-objects.rosh** - Objects on the Stack
Using objects with stack operations.

**Concepts:**
- Object references
- Stack-based object manipulation
- Object lifecycle

---

### **object-management.rosh** - Object Lifecycle
Creating, modifying, and destroying objects.

**Concepts:**
- Object creation patterns
- Memory management
- Object pools

---

### **type-annotations-demo.rosh** - Type Annotations
Adding type information to your code.

**Concepts:**
- Type declarations
- Type checking
- Type inference

**Example:**
```rosh
create object player: Character
    set health: Integer to 100
    set name: String to "Hero"
end
```

---

### **type-errors-demo.rosh** - Type Error Handling
Understanding and handling type errors.

**Concepts:**
- Type mismatches
- Error messages
- Debugging type issues

**Example:**
```rosh
# This will cause a type error
set health: Integer to "not a number"
```

---

## Key Advanced Concepts

### Inheritance

**Single inheritance:**
```rosh
create object hero from player
    set lives to 5
end
```

**Multiple inheritance:**
```rosh
create object boss from enemy, monster, magic_user
    set power to 100
end
```

**Property resolution:**
- Child properties override parent properties
- Multiple parents: left-to-right priority
- Deep inheritance chains supported

---

### Type System

**Basic types:**
- Integer, Float, String, Boolean
- Object, List, Dictionary

**Type annotations:**
```rosh
set score: Integer to 0
set name: String to "Player"
set alive: Boolean to true
```

**Type checking:**
- Runtime type validation
- Clear error messages
- Type coercion where safe

---

### Advanced Stack Operations

**Object manipulation:**
```rosh
create object item
get item  # Push to stack
duplicate  # Copy reference
swap  # Swap with another value
```

**Stack inspection:**
```rosh
stack_size  # Number of items
stack_dump  # Show all items
```

---

### Property Management

**Dynamic properties:**
```rosh
create object player
set "custom_property" to value  # Dynamic name
get player."custom_property"  # Dynamic access
```

**Property stacks:**
```rosh
set player.health to 100
set player.health to 50  # Replaces previous value
```

---

## Design Patterns

### Factory Pattern
```rosh
create object enemy_factory
    when spawn_enemy then
        create object enemy from base_enemy
        trigger enemy_spawned
    end
end
```

### Observer Pattern
```rosh
when player.health_changed then
    trigger update_ui
    trigger check_game_over
end
```

### Strategy Pattern
```rosh
create object ai_behavior
    set strategy to aggressive

    when update then
        if strategy equals aggressive then
            trigger attack
        end
    end
end
```

---

## Learning Path

1. **inheritance-single.rosh** - Start with basic inheritance
2. **inheritance-multiple.rosh** - Learn multi-parent inheritance
3. **for-loops.rosh** - Master iteration
4. **property-stacks.rosh** - Understand property mechanics
5. **type-annotations-demo.rosh** - Add type safety
6. **object-management.rosh** - Master object lifecycle

---

## Best Practices

### 1. Use Inheritance Wisely
- Keep inheritance hierarchies shallow
- Favor composition over deep inheritance
- Use multiple inheritance sparingly

### 2. Type Annotations
- Annotate public interfaces
- Use types for documentation
- Catch errors early

### 3. Property Management
- Use descriptive property names
- Group related properties
- Document dynamic properties

### 4. Code Organization
- One concept per file
- Use helper functions
- Keep files focused

---

## Common Patterns

### Singleton Pattern
```rosh
create object game_manager
    set instance to null

    when get_instance then
        if instance equals null then
            set instance to create_manager()
        end
        return instance
    end
end
```

### Command Pattern
```rosh
create object move_command
    when execute then
        set player.x to player.x plus 1
    end

    when undo then
        set player.x to player.x minus 1
    end
end
```

---

## Performance Tips

1. **Minimize object creation** - Reuse objects when possible
2. **Avoid deep inheritance** - Prefer flat hierarchies
3. **Use type annotations** - Helps interpreter optimize
4. **Profile your code** - Find bottlenecks before optimizing

---

## Next Steps

- Experiment with inheritance patterns
- Add types to your existing code
- Study the type-errors examples
- Build complex object hierarchies
- Combine with game examples to build sophisticated games!
