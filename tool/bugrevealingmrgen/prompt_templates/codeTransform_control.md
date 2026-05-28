# Code Refactoring: Control Structure Transformations

You are a code refactoring expert. Your task is to analyze the provided Java code and perform refactoring by transforming control structures.

## Instructions

1. Transform loop structures:
   - Convert `for` loops to `while` loops where appropriate
   - Convert `while` loops to `for` loops where appropriate

2. Transform conditional statements:
   - Convert `if-else` chains to `switch` statements where appropriate
   - Convert `switch` statements to `if-else` chains where appropriate

3. Loop decomposition:
   - Identify complex loops that can be split into multiple simpler loops
   - Ensure the decomposed loops maintain the same functionality
   - Consider performance implications of loop decomposition

4. Simplify conditional statements:
   - Break down complex `if` statements with multiple conditions
   - Split compound conditions into separate `if` statements
   - Maintain logical equivalence in the transformation


## Task: Java Code for Refactoring
```java
{Java_Code_for_Refactoring}
```

## Notes
- Preserve the semantic meaning of the code
- Ensure transformations not degrade code readability
- Consider performance implications of transformations
- Output only the refactored code, no explanations or additional text 

Output:
```java
{refactored_code}
```