# Task Description
<SYSTEM MESSAGE: START>
As an expert in Java programming and metamorphic testing, your role is to analyze a target method and identify meaningful **metamorphic relations** (MRs) involving it and other related methods. 
This includes understanding the functionality of the target method, the behavioral differences and relationships among methods within a class, and leveraging this understanding to formulate MRs and corresponding test cases.


Definitions:
**TARGET METHOD**: The method(s) under test.
**RELATED METHOD**: Any other method(s) in the class that can be used to construct metamorphic relations involving the TARGET METHOD.
(TARGET METHOD and RELATED METHOD can be the same or different methods.)

Your task is to:
1. Analyze the expected behavior of the **TARGET METHOD**.
2. Identify metamorphic relations by reasoning over **TARGET METHOD** and **RELATED METHOD**:
    * Consider if two inputs—one to the **TARGET METHOD** and another to a **RELATED METHOD**—satisfy a certain input relation.
    * Then determine if their corresponding outputs should also satisfy a certain output relation.
    * Leverage any functional overlap, symmetry, transformation logic, or other relationships between the methods.

    📌 Note: A single MR may involve multiple methods. Examples:
        * x = decode(encode(x)) → MR involving encode and decode
        * new MyClass(String x1) ≈ new MyClass(Float x2) → MR involving overloaded constructors
        * ...

3.	Write a test case that validates the MR you inferred:
    * The test case must include at least one invocation of the **TARGET METHOD**, one invocation of a **RELATED METHOD**, and a single assertion validating the MR (i.e., a property over their inputs and/or outputs).

Additional Notes:
* In addition to the **TARGET METHOD** and **RELATED METHOD**, you may use other methods (listed in the class under test's skeleton) to support your test case — for example, for input preparation, method invocations, or assertion.
* You may refer to **EXISTING TESTS** to help ensure your test case compiles and uses appropriate inputs and APIs.
* Your output may follow this pseudocode:
```java
@Test
public void testMR() {
    // Metamorphic Relation:
    // 1. Input Relation: Describe how follow-up input relates to source input
    // 2. Expected Output Relation: Describe how follow-up output should relate to source output

    // Inputs preparation
    InputType sourceInput = ...
    InputType followUpInput = ...

    // Invocation 1: invoke the target method with source input, and get the source output.
    OutputType sourceOutput = method1(sourceInput);

    // Invocation 2: invoke the related method with follow up input, and get the follow up output.
    OutputType followUpOutput = method2(followUpInput);

    // ONE assertion validating the relation over outputs and/or inputs. e.g., assertEquals(sourceOutput, followUpOutput);
    // (or use another appropriate assertion based on the MR)
    assert ... 
}
```
<SYSTEM MESSAGE: END>


# TARGET METHOD
```java
<FOCAL METHOD>
```

# RELATED METHODS
```java
<SUGGESTED METHODS>
```

# SKELETON of CLASS UNDER TEST
```java
<METHOD CONTEXT>
```

# EXISTING TESTS
```java
<EXISTING TESTS>
```

# REQUIRED DELIVERABLE
Only one MR-encoded test case is required.
``` java
public class $TestClassName$ {
    @Test
    public void testMR() {
        // Metamorphic Relation:
        // 1. Input Relation: Describe how follow-up input relates to source input
        // 2. Expected Output Relation: Describe how follow-up output should relate to source output

        // Inputs preparation

        // Invocation 1: invoke the target method with source input, and get the source output.
        
        // Invocation 2: invoke the related method with follow up input, and get the follow up output.

        // ONE assertion validating the relation over outputs and/or inputs.
    }
}
```

After deducing ONE metamorphic relation (MR), generate a corresponding test case by complementing the above code skeleton in 'REQUIRED DELIVERABLE'.


# Validation Checklist
- [ ] Includes at least two method invocations (one to **TARGET METHOD**, another to **RELATED METHOD**).
- [ ] Contains one assertion statement to validate the relation over their outputs and/or inputs