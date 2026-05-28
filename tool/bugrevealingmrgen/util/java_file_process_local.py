"""
Java file processing utilities for extracting class information
"""

import os
import re
from typing import List, Optional, Dict
import hashlib
try:
    import javalang
    JAVALANG_AVAILABLE = True
except ImportError:
    JAVALANG_AVAILABLE = False


def get_defined_classes(path_java_class_file: str) -> List[str]:
    """
    Extract only inner class names defined at class level in a Java file.
    Excludes local classes defined inside methods or functions.
    
    Args:
        path_java_class_file: Path to the Java file
        
    Returns:
        List of inner class names defined at class level.
        Returns fully qualified names when package information is available.
        Excludes the main/outer class and any local classes in methods.
    """
    if not os.path.exists(path_java_class_file):
        return []
    
    try:
        with open(path_java_class_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return []
    
    # Skip if content appears to be a template or non-Java file
    if content.strip().startswith('#') or '${' in content or '#set' in content:
        return []
    
    defined_classes = []
    
    # Extract package name
    package_name = _extract_package_name(content)
    
    # Try using javalang first (more accurate)
    if JAVALANG_AVAILABLE:
        try:
            tree = javalang.parse.parse(content)
            defined_classes = _extract_classes_with_javalang(tree, package_name)
            if defined_classes:
                return defined_classes
        except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError):
            pass  # Fall back to regex
    
    # Fallback to regex parsing
    defined_classes = _extract_classes_with_regex(content, package_name)
    return defined_classes


def _extract_package_name(content: str) -> Optional[str]:
    """Extract package name from Java file content."""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("package ") and line.endswith(";"):
            return line[8:-1].strip()  # Remove "package " and ";"
    return None


def _extract_classes_with_javalang(tree, package_name: Optional[str]) -> List[str]:
    """Extract only inner class names using javalang parser."""
    inner_classes = []
    
    # Find all top-level class declarations and extract their inner classes only
    for _, cls in tree.filter(javalang.tree.ClassDeclaration):
        class_name = cls.name
        if package_name:
            class_fqn = f"{package_name}.{class_name}"
        else:
            class_fqn = class_name
        
        # Only extract inner classes, not the main class itself
        _extract_inner_classes_only(cls, class_fqn, inner_classes)
    
    # Find all interface declarations and extract their inner classes
    for _, interface in tree.filter(javalang.tree.InterfaceDeclaration):
        interface_name = interface.name
        if package_name:
            interface_fqn = f"{package_name}.{interface_name}"
        else:
            interface_fqn = interface_name
        
        # Only extract inner classes/interfaces, not the main interface itself
        _extract_inner_classes_only(interface, interface_fqn, inner_classes)
    
    # Find all enum declarations and extract their inner classes
    for _, enum in tree.filter(javalang.tree.EnumDeclaration):
        enum_name = enum.name
        if package_name:
            enum_fqn = f"{package_name}.{enum_name}"
        else:
            enum_fqn = enum_name
        
        # Only extract inner classes, not the main enum itself
        _extract_inner_classes_only(enum, enum_fqn, inner_classes)
    
    return inner_classes


def _extract_inner_classes_only(parent_node, parent_fqn: str, inner_classes: List[str]):
    """
    Extract only inner classes defined at class level (not in methods).
    This excludes local classes defined inside methods or functions.
    """
    if not hasattr(parent_node, 'body') or not parent_node.body:
        return
        
    for member in parent_node.body:
        # Only look for classes/interfaces/enums that are direct members of the class
        # (not inside methods/constructors)
        if isinstance(member, javalang.tree.ClassDeclaration):
            inner_class_fqn = f"{parent_fqn}.{member.name}"
            inner_classes.append(inner_class_fqn)
            # Recursively extract nested inner classes
            _extract_inner_classes_only(member, inner_class_fqn, inner_classes)
        elif isinstance(member, javalang.tree.InterfaceDeclaration):
            inner_interface_fqn = f"{parent_fqn}.{member.name}"
            inner_classes.append(inner_interface_fqn)
            _extract_inner_classes_only(member, inner_interface_fqn, inner_classes)
        elif isinstance(member, javalang.tree.EnumDeclaration):
            inner_enum_fqn = f"{parent_fqn}.{member.name}"
            inner_classes.append(inner_enum_fqn)
        # Skip MethodDeclaration and ConstructorDeclaration - we don't want classes defined inside them


def _extract_classes_with_regex(content: str, package_name: Optional[str]) -> List[str]:
    """Extract only inner class names using regex as fallback."""
    inner_classes = []
    
    # Split content into lines for analysis
    lines = content.splitlines()
    
    # Track nesting level to identify inner classes vs local classes
    brace_level = 0
    in_method = False
    method_brace_level = 0
    
    # Pattern to match class, interface, and enum declarations
    class_pattern = re.compile(
        r'^\s*(?:public\s+|private\s+|protected\s+|static\s+|final\s+|abstract\s+)*'
        r'(?:class|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)'
    )
    
    # Pattern to match method/constructor declarations
    method_pattern = re.compile(
        r'^\s*(?:@\w+\s+)*(?:public|private|protected)?\s*(?:static\s+)?'
        r'(?:[\w<>\[\], ]+\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w, ]+)?\s*\{'
    )
    
    for line in lines:
        stripped = line.strip()
        
        # Count braces to track nesting
        open_braces = line.count('{')
        close_braces = line.count('}')
        
        # Check if we're entering/leaving a method
        if method_pattern.match(line) and brace_level > 0:  # Inside a class
            in_method = True
            method_brace_level = brace_level
        
        # Update brace level
        brace_level += open_braces - close_braces
        
        # Check if we're leaving a method
        if in_method and brace_level <= method_brace_level:
            in_method = False
        
        # Look for class declarations
        match = class_pattern.match(line)
        if match:
            class_name = match.group(1)
            
            # Only include if:
            # 1. We're inside a class (brace_level > 0)
            # 2. We're NOT inside a method
            if brace_level > 0 and not in_method:
                if package_name:
                    # For simplicity in regex fallback, just use the class name
                    # The full FQN construction would require tracking the outer class
                    inner_classes.append(class_name)
                else:
                    inner_classes.append(class_name)
    
    return inner_classes


def get_creation_examples(path_java_class_file: str, class_names: List[str]) -> Dict[str, List[str]]:
    """
    Find the functions/tests in the file that create instances of the specified class names.
    
    Args:
        path_java_class_file: Path to the Java file to analyze
        class_names: List of class names to look for instantiations of
        
    Returns:
        Dictionary mapping class names to lists of method code snippets that create instances
        {class_name: [function/test_code_snippet1, ...]}
    """
    if not os.path.exists(path_java_class_file) or not class_names:
        return {}
    
    try:
        with open(path_java_class_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return {}
    
    # Skip if content appears to be a template or non-Java file
    if content.strip().startswith('#') or '${' in content or '#set' in content:
        return {}
    
    creation_examples = {}
    
    # Try using javalang first (more accurate)
    if JAVALANG_AVAILABLE:
        try:
            tree = javalang.parse.parse(content)
            creation_examples = _find_creation_examples_with_javalang(tree, content, class_names)
            if creation_examples:
                return creation_examples
        except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError):
            pass  # Fall back to regex
    
    # Fallback to regex parsing
    creation_examples = _find_creation_examples_with_regex(content, class_names)
    return creation_examples


def _find_creation_examples_with_javalang(tree, content: str, class_names: List[str]) -> Dict[str, List[str]]:
    """Find creation examples using javalang parser."""
    creation_examples = {}
    
    # Convert class names to simple names for easier matching
    simple_class_names = [name.split('.')[-1] for name in class_names]
    class_name_mapping = {simple: full for simple, full in zip(simple_class_names, class_names)}
    
    # Find all classes in the file
    for _, cls in tree.filter(javalang.tree.ClassDeclaration):
        if not cls.methods:
            continue
            
        # Analyze each method
        for method in cls.methods:
            if not method or not hasattr(method, 'position') or not method.position:
                continue
                
            try:
                start_line = method.position.line
                method_code, _ = _get_method_code(content, start_line)
                
                # Check if this method contains instantiation of any target classes
                for simple_name in simple_class_names:
                    instantiation_patterns = [
                        f"new {simple_name}(",
                        f"new {simple_name} (",
                        f"{simple_name}.builder()",
                        f"{simple_name}.create()",
                        f"{simple_name}.getInstance()"
                    ]
                    
                    if any(pattern in method_code for pattern in instantiation_patterns):
                        full_class_name = class_name_mapping[simple_name]
                        if full_class_name not in creation_examples:
                            creation_examples[full_class_name] = []
                        creation_examples[full_class_name].append(method_code)
                        
            except Exception:
                continue  # Skip methods that can't be processed
    
    return creation_examples


def _find_creation_examples_with_regex(content: str, class_names: List[str]) -> Dict[str, List[str]]:
    """Find creation examples using regex as fallback."""
    creation_examples = {}
    
    # Convert class names to simple names for easier matching
    simple_class_names = [name.split('.')[-1] for name in class_names]
    class_name_mapping = {simple: full for simple, full in zip(simple_class_names, class_names)}
    
    lines = content.splitlines()
    
    # Pattern to match method declarations
    method_pattern = re.compile(
        r'^\s*(?:@\w+\s+)*(?:public|private|protected)?\s*(?:static\s+)?'
        r'(?:[\w<>\[\], ]+\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w, ]+)?\s*\{'
    )
    
    i = 0
    while i < len(lines):
        line = lines[i]
        match = method_pattern.match(line)
        
        if match:
            # Found a method, extract its full code
            method_start = i
            brace_count = line.count('{') - line.count('}')
            method_lines = [line]
            i += 1
            
            # Find the end of the method
            while i < len(lines) and brace_count > 0:
                line = lines[i]
                method_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                i += 1
            
            method_code = '\n'.join(method_lines)
            
            # Check if this method contains instantiation of any target classes
            for simple_name in simple_class_names:
                instantiation_patterns = [
                    f"new {simple_name}(",
                    f"new {simple_name} (",
                    f"{simple_name}.builder()",
                    f"{simple_name}.create()",
                    f"{simple_name}.getInstance()"
                ]
                
                if any(pattern in method_code for pattern in instantiation_patterns):
                    full_class_name = class_name_mapping[simple_name]
                    if full_class_name not in creation_examples:
                        creation_examples[full_class_name] = []
                    creation_examples[full_class_name].append(method_code)
                    break  # Don't add the same method multiple times
        else:
            i += 1
    
    return creation_examples


def _get_method_code(content: str, start_line: int) -> tuple[str, str]:
    """Extract method code starting from a given line number."""
    lines = content.split('\n')
    start_idx = start_line - 1
    if start_idx >= len(lines):
        return ("", hashlib.md5("".encode()).hexdigest())
    
    brace_count = 0
    code_lines = []
    found_brace = False
    
    for idx in range(start_idx, len(lines)):
        line = lines[idx]
        code_lines.append(line)
        if idx == start_idx:
            if '{' in line:
                brace_count += line.count('{')
                found_brace = True
            else:
                continue
        else:
            if not found_brace:
                if '{' in line:
                    brace_count += line.count('{')
                    found_brace = True
                else:
                    continue
        
        brace_count += line.count('{') - line.count('}')
        if brace_count <= 0:
            break
    
    code = '\n'.join(code_lines)
    return (code, hashlib.md5(code.encode()).hexdigest())
    
    


def test_get_defined_classes():
    test_class_file = "/data/projects/example-project/src/test/java/org/example/rules/core/RuleProxyTest.java"
    if os.path.exists(test_class_file):
        defined_classes = get_defined_classes(test_class_file)
        print(f"Classes found in {test_class_file}:")
        for cls in defined_classes:
            print(f"  - {cls}")
    else:
        print(f"File not found: {test_class_file}")

def test_get_creation_examples():
    test_class_file = "/data/projects/example-project/src/test/java/org/example/rules/core/RuleProxyTest.java"
    class_names = ["DummyRule"]
    creation_examples = get_creation_examples(test_class_file, class_names)
    for class_name, examples in creation_examples.items():
        print(f"Class: {class_name}")
        for example in examples:
            print(f"{example}")
            print()


if __name__ == "__main__":
    test_get_defined_classes()
    test_get_creation_examples()