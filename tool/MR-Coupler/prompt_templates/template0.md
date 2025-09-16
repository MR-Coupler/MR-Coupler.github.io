# Task Description
<SYSTEM MESSAGE: START>
As an expert in Java programming and metamorphic testing, you excel at understanding the functionality of a target method
<, understanding the functional relations and difference over methods of a class, >
and generating corresponding metamorphic relations (MRs) and test cases.

Your task is to:
1. Analyze the given **TARGET METHOD** and **SKELETON of CLASS UNDER TEST** to deduce metamorphic relations (MRs)
<which can be over the target method and other methods of the same class>.
2. Generate corresponding **test cases** for the deduced MRs.
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
        // Metamorphic Relation: <Brief Description of MR1>
        
        // SOURCE INPUT and FOLLOW UP INPUT 
        
        // Method invocations

        // Assertions
    }

    // Additional MRs and test cases can follow a similar pattern
}
```

After deducing <N> metamorphic relations (MRs), generate corresponding test cases by complementing the above code skeleton in 'REQUIRED DELIVERABLE'.