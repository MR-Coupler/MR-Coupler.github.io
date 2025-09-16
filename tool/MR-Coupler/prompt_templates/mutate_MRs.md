# Metamorphic Test Case Mutation

## Problem Statement
Some metamorphic test cases (MTCs) are valid but not bug-revealing because they rely on specific constructors or methods that may be not buggy. By trying different ways to construct input objects, we can potentially reveal bugs that would otherwise remain hidden.

## Task
Update the provided MTCs to make them potentially bug-revealing by:
1. Trying alternative constructors and methods
2. Using different input object construction approaches
3. Exploring various method combinations
4. Maintaining the same metamorphic relation while changing implementation details

## Examples of Bug-Revealing vs Non-Bug-Revealing MTCs
### Example 1: Different Methods
```java
@Test
public void testMR1() {
    // MR: Enforce(BigDecimal).doubleValue() should equal enforce(enforce(BigDecimal).doubleValue())
    // Ensures consistency between BigDecimal and double enforce methods

    // Non-bug-revealing version
    // NumberContext context = NumberContext.of(5, 2);
    
    // Bug-revealing version - by using another method
    NumberContext context = NumberContext.ofPrecision(5);

    BigDecimal original = new BigDecimal("123.4567");
    BigDecimal enforcedBigDecimal = context.enforce(original);
    double enforcedDouble = context.enforce(original.doubleValue());

    TestUtils.assertEquals(enforcedBigDecimal.doubleValue(), enforcedDouble);
}
```

### Example 2: Different Object Types
```java
@Test
public void testMR2() {
    // MR: Handles unary joints (same body)
    ConstraintGraph<Body> g = new ConstraintGraph<>();
    Body b = new Body();
    g.addBody(b);
    
    // Non-bug-revealing version
    // Vector2 anchor = new Vector2(0, 0);
    // Joint<Body> joint = new DistanceJoint<>(b, b, anchor, anchor);
    
    // Bug-revealing version - by using another object type
    Joint<Body> joint = new PinJoint<Body>(b, b.getWorldCenter(), 8.0, 0.1, 1000);
    g.addJoint(joint);
    
    assertTrue(g.containsJoint(joint));
    g.removeBody(b);
    assertFalse(g.containsJoint(joint));
    assertNull(g.getNode(b));
}
```

## Guidelines for Mutation

1. Object Construction:
   - Try different constructors with various parameters
   - Use alternative factory methods
   - Consider different initialization approaches
   - Explore different object types that satisfy the same interface

2. Method Usage:
   - Try different method combinations
   - Use alternative method overloads
   - Consider different parameter orders
   - Explore different method chains

3. Input Data:
   - Try different input values
   - Use alternative data types
   - Consider edge cases
   - Explore boundary conditions

4. Naming Convention:
   - Name new test methods as: `updated{N}_testMR{M}()`
   - Keep original test methods unchanged
   - Add clear comments explaining the mutation

## Required Deliverable
Given the following class of MTCs, for each MTC, create five mutated MTCs that try different approaches to construct input objects. Refer to the Class Under Test (CUT) and existing tests to identify alternative constructors and methods. Just return the updated class. 

```java
<GENERATED MTCs>
```

### SKELETON of CLASS UNDER TEST
```java
<METHOD CONTEXT>
```

### EXISTING TESTS
```java
<EXISTING TESTS>
```


## Notes
- Ensure mutated tests are still valid and compilable
- Focus on different object construction approaches
- Keep original test methods for comparison. For each original MTC, You just need to add five new mutated MTCs (e.g., `updated1_testMR1()`, `updated2_testMR1()`, ....).
- Just return the updated class with original MTCs and new MTCs in the form of:    
```java
{updated_class}
```

