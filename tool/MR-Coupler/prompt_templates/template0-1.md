# Task Description
<SYSTEM MESSAGE: START>
As an expert in Java programming and metamorphic testing, you excel at understanding the functionality of a target method, understanding the functional relations and difference over methods of a class,
and generating corresponding metamorphic relations (MRs) and test cases.

A metamorphic relation (MR) is a relationship between multiple inputs and outputs of programs.
Instead of checking exact outputs, MRs describe how outputs should change (or not change) in response to specific changes in the input.

Your task is to:
1. Analyze the given **TARGET METHOD** and **SKELETON of CLASS UNDER TEST** to deduce metamorphic relations (MRs)
<which can be over the target method and other methods of the same class>.
2. Generate corresponding **MR-encoded test cases** for the deduced MRs. The following is the template: 

MR-encoded Test Case Template (Pseudocode):
```java
@Test
public void testMR() {
    // Metamorphic Relation: 
    // 1. Relation Type: [Identity/Additive/Multiplicative/Permutation/Inversion/Equivalence/ ...]
    // 2. Input Relation: [Describe how the follow-up input relates to the source input]
    // 3. Expected Output Relation: [Describe how the follow-up output should relate to the source output]
    // 4. Rationale: [Explain why this relation should hold based on the method's functionality]
    
    // invocation1: invoke the target method with source input, and get the source output.
    sourceOutput = targetMethod1(sourceInput);
    // invocation2: invoke the target method with follow up input, and get the follow up output.
    followUpOutput = targetMethod2(followUpInput);
    
    ...
    // one assertion statement: validate either (1) sourceOutput vs followUpOutput relation (where sourceOutput and followUpOutput must included in the same assertion statement),  OR (2) sourceInput vs followUpOutput relation (where sourceInput and followUpOutput must included). 
    assertEquals(sourceOutput, followUpOutput);  OR assertEquals(sourceInput, followUpOutput); // This is just an example — output relations can be diverse and are not limited to equality.
}
```
Note:
1. Do not use `while`, `for`, `if` in the test case. 
2. There are two following necessary conditions for a test case to be a valid MR-encoded test case:
* (1) The test case must contain at least two invocations to target methods with two inputs separately.  The two target method invocations (`targetMethod1` and `targetMethod2`) can be the same or different methods in the class under test.
* (2) The test case must contain at least one assertion that validates the relation between the inputs and outputs of the above method invocations.
3. The test case must be a valid MR-encoded test case.
<SYSTEM MESSAGE: END>


# TARGET METHOD
```java
<FOCAL METHOD>
```


# SKELETON of CLASS UNDER TEST
```java
<METHOD CONTEXT>
```


# REQUIRED DELIVERABLE
``` java
public class $TestClassName$ {
    @Test
    public void testMR1() {
        // Metamorphic Relation: 
        // 1. Relation Type: [Identity/Additive/Multiplicative/Permutation/Inversion/Equivalence/ ...]
        // 2. Input Relation: [Describe how the follow-up input relates to the source input]
        // 3. Expected Output Relation: [Describe how the follow-up output should relate to the source output]
        // 4. Rationale: [Explain why this relation should hold based on the method's functionality]
    
        // invocation1: invoke the target method with source input, and get the source output.

        // invocation2: invoke the target method with follow up input, and get the follow up output.

        // one assertion statement: validate either (1) sourceOutput vs followUpOutput relation (where sourceOutput and followUpOutput must included in the same assertion statement),  OR (2) sourceInput vs followUpOutput relation (where sourceInput and followUpOutput must included). 

    }

    // Additional MRs and test cases can follow a similar pattern
}
```

After deducing <N> metamorphic relations (MRs), generate corresponding MR-encoded test cases by complementing the above code skeleton in 'REQUIRED DELIVERABLE'.

You should follow the following rules:
1. Do not use `while`, `for`, `if` in the test case. 
2. The test case must be a valid MR-encoded test case.
There are two following necessary conditions for a test case to be a valid MR-encoded test case:
* (1) The test case must contain at least two invocations to target methods with two inputs separately.  The two target method invocations (`targetMethod1` and `targetMethod2`) can be the same or different methods in the class under test.
* (2) The test case must contain at least one assertion that validates the relation between the inputs and outputs of the above method invocations.

The following is the template for an MR-encoded test case (Pseudocode):
```java
@Test
public void testMR() {
    // Metamorphic Relation: <Brief Description of MR1>
    
    // invocation1: invoke the targetMethod1 with source input, and get the source output.
    sourceOutput = targetMethod1(sourceInput);
    // invocation2: invoke the targetMethod2 with follow up input, and get the follow up output.
    followUpOutput = targetMethod2(followUpInput);
    
    ...
    // one assertion statement: validate either (1) sourceOutput vs followUpOutput relation (where sourceOutput and followUpOutput must included in the same assertion statement),  OR (2) sourceInput vs followUpOutput relation (where sourceInput and followUpOutput must included). 
    assertEquals(sourceOutput, followUpOutput);  OR assertEquals(sourceInput, followUpOutput); // This is just an example — output relations can be diverse and are not limited to equality.
}
```

# MTC Validation Checklist
- [ ] Contains at least two method invocations
- [ ] Has clear input relations and output relationss
- [ ] Includes appropriate assertions to validate the output relations