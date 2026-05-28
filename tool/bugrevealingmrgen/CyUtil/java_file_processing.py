#!/usr/bin/env python
# encoding: utf-8
"""

Created on 2022/11/22
@Author : 

用于进行Java文件相关操作
"""
import os,sys
import os.path
import shutil
import tarfile
import time
import re

import json, os, sys

_PROJECT_NAME = "CyUtil"
_CURRENT_ABSPATH = os.path.abspath(__file__)
sys.path.insert(0, _CURRENT_ABSPATH[:_CURRENT_ABSPATH.find(_PROJECT_NAME) + len(_PROJECT_NAME) + 1])

import re
import traceback
import itertools

import file_processing
import config
import java_parser

import javalang # type: ignore
from javalang.tree import Annotation, MethodDeclaration, ClassDeclaration # type: ignore

Junit_helper_methods_annotations = [
    "@setUp",
    "@BeforeClass",
    "@Before",
    "@BeforeAll",
    "@After",
    "@AfterClass",
    "@AfterAll",
] 


def get_class_FQS_from_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    class_name = file_path.split("/")[-1].replace(".java", "")
    package_name = ""
    for line in lines:
        if line.startswith("package "):
            package_name = line.split("package ")[1].replace(";", "").strip()
            break
    FQN_ = package_name + "." + class_name
    return FQN_


def get_all_class_path(dir, include_test_classes=False, poj_build_tool= "maven"):
    class_dir_list = []
    dir_list = file_processing.walk_allDirs(dir)
    if poj_build_tool.lower() == "maven":
        for dir_ in dir_list:
            if '/target/classes' in dir_:
                class_str = dir_.split("/target/classes")[0] + "/target/classes"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )
            if include_test_classes and '/target/test-classes' in dir_ :
                class_str = dir_.split("/target/test-classes")[0] + "/target/test-classes"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )
    elif poj_build_tool.lower() == "gradle":
        for dir_ in dir_list:
            if '/build/classes/java/main/' in dir_:
                class_str = dir_.split("/build/classes/java/main/")[0] + "/build/classes/java/main/"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )
            if include_test_classes and '/build/classes/java/test/' in dir_ :
                class_str = dir_.split("/build/classes/java/test/")[0] + "/build/classes/java/test/"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )

    return class_dir_list


def get_all_target_classes_and_jars_relative_path(dir, include_test_classes=False, poj_build_tool= "maven"):
    """
    Get relative paths for both classes and JAR files in a Java project.
    
    Args:
        dir (str): Path to the Java project root directory
        include_test_classes (bool): Whether to include test classes paths
        poj_build_tool (str): Build tool used ("maven" or "gradle")
        
    Returns:
        tuple: (class_relative_dir_list, jar_files_list) - Lists of relative paths
               for class directories and JAR files
    """
    # Get class paths (reuse existing function)
    class_relative_dir_list = get_all_class_relative_path(dir, include_test_classes, poj_build_tool)
    
    # Find JAR files
    jar_files_list = []
    dir_list = file_processing.walk_allDirs(dir)
    
    if poj_build_tool.lower() == "maven":
        # Find JARs in Maven project
        for dir_ in dir_list:
            # print(dir_)
            # Look for JARs in Maven repository directories
            if '/target/dependency' in dir_:
                jar_files = [os.path.join(dir_, file) for file in os.listdir(dir_) if file.endswith('.jar')]
                for jar in jar_files:
                    if jar not in jar_files_list:
                        jar_files_list.append(jar)
            if '/target' in dir_:
                jar_files = [os.path.join(dir_, file) for file in os.listdir(dir_) if file.endswith('.jar')]
                for jar in jar_files:
                    if jar not in jar_files_list:
                        jar_files_list.append(jar)
                        
            # Look for JARs in lib directories
            if '/lib/' in dir_:
                jar_files = [os.path.join(dir_, file) for file in os.listdir(dir_) if file.endswith('.jar')]
                for jar in jar_files:
                    if jar not in jar_files_list:
                        jar_files_list.append(jar)
                        
    elif poj_build_tool.lower() == "gradle":
        # Find JARs in Gradle project
        for dir_ in dir_list:
            # Look for JARs in Gradle dependency directories
            if '/build/libs' in dir_ or '/build/dependency' in dir_:
                jar_files = [os.path.join(dir_, file) for file in os.listdir(dir_) if file.endswith('.jar')]
                for jar in jar_files:
                    if jar not in jar_files_list:
                        jar_files_list.append(jar)
            
            # Look for JARs in lib directories
            if '/lib' in dir_:
                jar_files = [os.path.join(dir_, file) for file in os.listdir(dir_) if file.endswith('.jar')]
                for jar in jar_files:
                    if jar not in jar_files_list:
                        jar_files_list.append(jar)
    
    # Convert to relative paths
    jar_relative_files_list = []
    for jar_path in jar_files_list:
        if jar_path.startswith(dir):
            jar_relative_files_list.append(jar_path.replace(dir, ""))
        else:
            jar_relative_files_list.append(jar_path)
    
    return class_relative_dir_list, jar_relative_files_list


def get_all_class_relative_path(dir, include_test_classes=False, poj_build_tool= "maven", specific_dependency_folder=False):
    if specific_dependency_folder==False:
        specific_dependency_folder = dir
    class_dir_list = []
    dir_list = file_processing.walk_allDirs(dir)
    if poj_build_tool.lower() == "maven":
        for dir_ in dir_list:
            if '/target/dependency' in dir_ and specific_dependency_folder in dir_:
                class_str = dir_.split("/target/dependency")[0] + "/target/dependency/*"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )
            if '/target/classes' in dir_:
                class_str = dir_.split("/target/classes")[0] + "/target/classes"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )
            if include_test_classes and '/target/test-classes' in dir_ :
                class_str = dir_.split("/target/test-classes")[0] + "/target/test-classes"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )
    elif poj_build_tool.lower() == "gradle":
        for dir_ in dir_list:
            if '/build/dependency/' in dir_ and specific_dependency_folder in dir_: # to modify
                class_str = dir_.split("/build/dependency/")[0] + "/build/dependency/*"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )
            if '/build/classes/java/main/' in dir_:
                class_str = dir_.split("/build/classes/java/main/")[0] + "/build/classes/java/main/"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )
            if include_test_classes and '/build/classes/java/test/' in dir_ :
                class_str = dir_.split("/build/classes/java/test/")[0] + "/build/classes/java/test/"
                if class_str not in class_dir_list:
                    class_dir_list.append( class_str )

    class_relative_dir_list = []
    for ele in class_dir_list:
        if ele.startswith(dir):
            class_relative_dir_list.append( ele.replace(dir,"") )
        else:
            class_relative_dir_list.append( ele )
    return class_relative_dir_list


def find_asserts_in_java_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    assertionLines = {}
    for line_number, line in enumerate(lines, start=1):
        if 'assert' in line and not line.startswith("import ") :
            assertionLines[line_number] = line.strip()
            # print(f'Line {line_number}: {line.strip()}')
    return assertionLines


def find_class_file_path_by_methodFQS(poj_dir, method_fqs):
    # Step 1: Derive class name and relative path from method FQS
    FQN_method = method_fqs.split('(')[0]
    package_class_part = FQN_method.rsplit('.', 1)[0]
    relative_class_path = package_class_part.replace('.', '/') + '.java'
    # print(f"Relative class path: {relative_class_path}", package_class_part)
    parent_package_class_part = package_class_part.rsplit('.', 1)[0]
    parent_relative_class_path = parent_package_class_part.replace('.', '/') + '.java'
    # print(f"parent Relative class path: {parent_relative_class_path}", parent_package_class_part)

    found_file_path = ""
    # Step 2: Search for the Java file
    for root, dirs, files in os.walk(poj_dir):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                # Check if this file's path ends with the package path derived from FQS
                if file_path.endswith(relative_class_path):
                    found_file_path = file_path
                    return found_file_path  # Found the corresponding class file path
    if found_file_path=="": # may package_class_part is the subclass
        # Step 3: Search for the parenta Java file
        for root, dirs, files in os.walk(poj_dir):
            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    # Check if this file's path ends with the package path derived from FQS
                    if file_path.endswith(parent_relative_class_path):
                        found_file_path = file_path
                        return found_file_path  # Found the corresponding class file path
    
    return None  # If no file is found


def get_class_fully_qualified_names(target_class_pathes):
    fqns = []
    for path in target_class_pathes:
        class_name = os.path.splitext(os.path.basename(path))[0]
        package = None
        
        # Extract package name from the Java file
        with open(path, 'r', encoding='utf-8') as file:
            for line in file:
                stripped_line = line.strip()
                if stripped_line.startswith('package '):
                    # Split line at ';' and extract the package
                    package_declaration = stripped_line.split(';', 1)[0]
                    package = package_declaration.split(' ', 1)[1].strip()
                    break
        
        # Build the FQN
        if package:
            fqn = f"{package}.{class_name}"
        else:
            fqn = class_name  # Default package
        
        fqns.append(fqn)
    
    return fqns

def get_skeleton_of_class(class_file_path):
    """
    Get the skeleton of a class by keeping the structure but replacing method bodies with "...".
    
    Args:
        class_file_path (str): Path to the Java class file
        
    Returns:
        str: Class skeleton with method bodies replaced by "... // just obmitted method body"
    """
    try:
        # Read the file content
        with open(class_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Parse the Java code
        tree = javalang.parse.parse(content)
        lines = content.split('\n')
        
        # Keep track of regions to replace
        regions_to_replace = []
        
        # Process all method declarations
        for path, node in tree.filter(MethodDeclaration):
            if not hasattr(node, 'position') or not node.position:
                continue
                
            start_line, start_col = node.position
            
            # Find the method body's start and end
            brace_count = 0
            body_start = None
            body_end = None
            
            # Find the opening brace of method body
            for i in range(start_line - 1, len(lines)):
                if '{' in lines[i]:
                    body_start = i
                    brace_count = 1
                    # Continue counting braces until we find the matching closing brace
                    for j in range(i + 1, len(lines)):
                        brace_count += lines[j].count('{')
                        brace_count -= lines[j].count('}')
                        if brace_count == 0:
                            body_end = j
                            break
                    break
            
            if body_start is not None and body_end is not None:
                regions_to_replace.append((body_start, body_end))
        
        # Sort regions in reverse order to avoid index shifting
        regions_to_replace.sort(reverse=True)
        
        # Create new lines list
        new_lines = lines.copy()
        
        # Replace method bodies with "..."
        for start, end in regions_to_replace:
            # Keep the opening brace line
            opening_line = new_lines[start]
            # Find position of opening brace
            brace_pos = opening_line.find('{')
            if brace_pos != -1:
                # Keep everything up to and including the opening brace
                new_lines[start] = opening_line[:brace_pos + 1]
                # Add indentation for ...
                indent = ' ' * (len(opening_line) - len(opening_line.lstrip()))
                new_lines[start + 1:end] = [f"{indent}    ..."]
                # Keep closing brace with proper indentation
                new_lines[end] = indent + '}'
        
        # Reconstruct the file content
        skeleton = '\n'.join(new_lines)
        
        return skeleton
        
    except Exception as e:
        print(f"Error processing class file: {str(e)}")
        return None


def keep_relevant_tests(test_file_content, target_methods_FQS):
    """
    Filter and keep the most relevant test cases from the test file content.
    
    Args:
        test_file_content (str): Content of the test file
        target_methods_FQS (list): List of fully qualified names of target methods
        
    Returns:
        str: Filtered test file content containing only relevant test cases
    """
    # Extract target method names and parameter types
    target_info = []
    for fqn in target_methods_FQS:
        method_sig = fqn.split("(")[0]
        method_name = method_sig.split(".")[-1]
        param_types = []
        if "(" in fqn and ")" in fqn:
            params = fqn.split("(")[1].split(")")[0]
            if params:
                param_types = [p.split(" ")[0].strip() for p in params.split(",")]
        target_info.append({
            "name": method_name,
            "params": param_types
        })
    
    # Split test file into individual test methods
    lines = test_file_content.split("\n")
    test_methods = []
    current_method = []
    in_method = False
    method_name = ""
    
    for line in lines:
        # Start of a test method
        if "@Test" in line or (not in_method and "test" in line.lower() and "public" in line.lower() and "void" in line.lower()):
            if current_method:
                test_methods.append({"name": method_name, "content": "\n".join(current_method)})
            current_method = []
            in_method = True
            method_name = line if "@Test" not in line else ""
            current_method.append(line)
        # End of a method
        elif in_method and line.strip() == "}":
            current_method.append(line)
            test_methods.append({"name": method_name, "content": "\n".join(current_method)})
            current_method = []
            in_method = False
        # Inside a method
        elif in_method:
            if not method_name and "void" in line:
                method_name = line
            current_method.append(line)
            
    # Score each test method based on relevance
    scored_methods = []
    for test_method in test_methods:
        score = 0
        content = test_method["content"].lower()
        
        # 1. Check for methods with similar names
        for target in target_info:
            if target["name"].lower() in content:
                score += 3  # High priority for name matches
            # Check for similar names (e.g., testAdd vs add)
            elif any(w for w in content.split() if target["name"].lower() in w):
                score += 2
                
        # 2. Check for parameter type usage
        for target in target_info:
            for param_type in target["params"]:
                param_base = param_type.split(".")[-1].lower()
                if param_base in content:
                    score += 2  # Medium priority for parameter type matches
                    
        # 3. Additional relevance factors
        # Check for assertion patterns
        if "assert" in content:
            score += 1
            
        # Check for error handling
        if "exception" in content or "throws" in content:
            score += 1
            
        # Check for setup/initialization patterns
        if "new " in content:
            score += 1
            
        scored_methods.append((score, test_method["content"]))
    
    # Sort by score and take top N most relevant tests
    scored_methods.sort(reverse=True)
    MAX_TESTS = 5  # Limit to 5 most relevant tests
    selected_methods = [method for score, method in scored_methods[:MAX_TESTS]]
    
    # Reconstruct file content with selected methods
    # Keep the class structure and imports
    header = []
    in_class = False
    for line in lines:
        if "class" in line and "{" in line:
            in_class = True
            header.append(line)
            break
        header.append(line)
    
    # Combine everything
    result = "\n".join(header) + "\n"
    result += "\n".join(selected_methods)
    result += "\n}"  # Close the class
    
    return result


def keep_relevant_tests_backup__(test_class_file_content, target_methods_FQS):
    """
    Filter and keep the most relevant test cases from the test file content.
    1. test cases that invoke methods whose names are the same/similar to target methods
    2. test cases that invoke methods whose parameters are the same/similar to target methods
    3. other relevant test cases as context for LLMs
    
    Args:
        test_class_file_content (str): Content of the test class file
        target_methods_FQS (list): List of fully qualified names of target methods
        
    Returns:
        str: Filtered test file content containing only relevant test cases
    """
    try:
        # Parse the Java code
        tree = javalang.parse.parse(test_class_file_content)
        
        # Extract target method information
        target_methods_info = []
        for method_fqs in target_methods_FQS:
            method_name = method_fqs.split('(')[0].split('.')[-1]
            # Extract parameter types from FQS
            param_types = []
            if '(' in method_fqs:
                params_str = method_fqs.split('(')[1].split(')')[0]
                if params_str:
                    param_types = [p.strip() for p in params_str.split(',')]
            target_methods_info.append({
                'name': method_name,
                'params': param_types,
                'name_parts': set(re.findall('[A-Z][a-z]*', method_name))  # Split camelCase
            })

        # Collect all test methods with their relevance scores
        test_methods = {}
        class_content = {}  # Store class content by line number
        lines = test_class_file_content.split('\n')
        
        for path, node in tree.filter(MethodDeclaration):
            if not hasattr(node, 'annotations') or not any(a.name == 'Test' for a in node.annotations):
                continue
                
            method_start, method_col = node.position
            method_body = []
            brace_count = 0
            for i in range(method_start - 1, len(lines)):
                line = lines[i]
                brace_count += line.count('{') - line.count('}')
                method_body.append(line)
                if brace_count == 0:
                    break
            
            method_content = '\n'.join(method_body)
            class_content[method_start] = {
                'name': node.name,
                'content': method_content,
                'score': 0
            }
            
            # Calculate relevance score for each test method
            for target in target_methods_info:
                score = 0
                
                # 1. Name similarity
                method_name_parts = set(re.findall('[A-Z][a-z]*', node.name))
                name_similarity = len(method_name_parts.intersection(target['name_parts']))
                score += name_similarity * 2
                
                # 2. Parameter type similarity
                if hasattr(node, 'parameters'):
                    test_param_types = [p.type.name for p in node.parameters]
                    param_similarity = len(set(test_param_types).intersection(set(target['params'])))
                    score += param_similarity * 2
                
                # 3. Method invocation similarity
                if target['name'] in method_content:
                    score += 3
                
                # 4. Similar assertion patterns
                assertion_count = sum(1 for pattern in [
                    'assert', 'verify', 'check', 'expect'
                ] if pattern in method_content.lower())
                score += min(assertion_count, 2)
                
                # 5. Setup/state similarity (checking field usage)
                if any(field.name in method_content for field in tree.filter(javalang.tree.FieldDeclaration)):
                    score += 1
                
                class_content[method_start]['score'] = max(
                    class_content[method_start]['score'], 
                    score
                )

        # Sort methods by relevance score
        relevant_methods = sorted(
            class_content.items(), 
            key=lambda x: x[1]['score'], 
            reverse=True
        )

        # Keep top N most relevant methods (adjust N as needed)
        N = 5
        kept_methods = set(method[0] for method in relevant_methods[:N])
        
        # Reconstruct the file content keeping only relevant methods
        filtered_lines = []
        current_method = None
        brace_count = 0
        
        # Keep class declaration and imports
        for i, line in enumerate(lines, 1):
            if 'class ' in line or line.strip().startswith('import ') or line.strip().startswith('package '):
                filtered_lines.append(line)
                continue
                
            # Track method boundaries
            if any(f"void {content['name']}" in line for _, content in class_content.items()):
                current_method = next(
                    (start for start, content in class_content.items() 
                     if f"void {content['name']}" in line),
                    None
                )
                
            if current_method is not None:
                if current_method in kept_methods:
                    filtered_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0:
                    current_method = None
            else:
                filtered_lines.append(line)
                
        return '\n'.join(filtered_lines)

    except Exception as e:
        print(f"Error processing test file: {str(e)}")
        return test_class_file_content  # Return original content in case of error


""" delete methods/tests """
def remove_test_cases(java_file_path: str, test_case_names: list) -> str:
    """
    Removes specified test cases from a Java test class file.
    
    :param java_file_path: Path to the Java test class file.
    :param test_case_names: List of test case method names to be removed.
    :return: Updated Java test class as a string.
    """
    # Read the Java file
    with open(java_file_path, 'r', encoding='utf-8') as file:
        java_code = file.read()
    
    lines = java_code.split('\n')
    lines_to_remove = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        for test_case in test_case_names:
            # Check if the line contains the method declaration
            pattern = r'\bvoid\s+' + re.escape(test_case) + r'\s*\('
            if re.search(pattern, line):
                # Found the test case to delete, backtrack to find annotations
                start = i
                j = i - 1
                while j >= 0 and lines[j].strip().startswith('@'):
                    start = j
                    j -= 1
                
                # Find the end of the method by counting braces
                brace_count = 0
                end = None
                for k in range(i, len(lines)):
                    brace_count += lines[k].count('{')
                    brace_count -= lines[k].count('}')
                    if brace_count > 0:
                        end = None  # Reset end until braces balance
                    if brace_count == 0 and end is None:
                        end = k
                        break
                if end is None:
                    end = len(lines) - 1  # Fallback if braces are unbalanced
                
                # Mark lines for removal
                for l in range(start, end + 1):
                    if l < len(lines):
                        lines_to_remove.add(l)
                # Skip processed lines
                i = end
                break
        i += 1
    
    # Generate the updated content
    updated_lines = [line for idx, line in enumerate(lines) if idx not in lines_to_remove]
    return '\n'.join(updated_lines)





""" comment methods/tests """
# 注意，只用于test class， 不要用于其他class；only_keep_target_method=True,
def comment_target_test_method(test_class_text, target_method_name, only_keep_target_method=False, keep_helper_methods=True):
    """
    helper_annotations = {'Before', 'After', 'BeforeClass', 'AfterClass',"setUp","BeforeAll","AfterAll"}
    Comment out methods in a Java class file, except for the target method.
    
    Args:
        test_class_text (str): The content of the Java class file.
        target_method_name (str): The name of the method to keep uncommented.
        only_keep_target_method (bool): If True, only the target method is uncommented.
        keep_helper_methods (bool): If True, helper methods with specific annotations are not commented out.
    
    Returns:
        str: The updated Java class content with methods commented out as specified.
    """

    lines = test_class_text.split('\n')
    output = []
    
    # 状态跟踪
    class_braces = []       # 类大括号计数器栈
    in_method = False       # 是否在方法体内
    in_comment_block = False# 是否在注释块中
    brace_count = 0         # 方法大括号嵌套计数
    current_annotations = [] # 当前方法关联的注解
    retain_current = False  # 是否保留当前方法
    method_start_idx = -1   # 待注释方法起始行
    
    # 正则表达式
    class_pattern = re.compile(r'^\s*(?:public|private|protected)?\s*class\s+\w+')
    method_pattern = re.compile(
        r'^\s*((?:@\w+\.?\w*\s+)*)'      # 捕获注解
        r'(?:public|protected|private|static|final|abstract|)\s+'  # 修饰符
        r'(?:[\w<>\[\],]+\s+)?'          # 返回类型（支持泛型）
        r'(\w+)\s*\([^)]*\)'             # 方法名和参数
    )
    # helper_annotations = {'Test', 'Before', 'After', 'BeforeClass', 'AfterClass', 'Rule'}
    # helper_annotations = {'Before', 'After', 'BeforeClass', 'AfterClass',"setUp","BeforeAll","AfterAll"}
    helper_annotations = ['setUp', 'Before', 'BeforeAll', 'BeforeClass', 'After', 'AfterAll', 'AfterClass']
    

    for idx, line in enumerate(lines):
        stripped = line.strip()
        original_line = line
        
        # 处理注释块状态
        if '/*' in line and '*/' not in line:
            in_comment_block = True
        elif '*/' in line:
            in_comment_block = False
        if in_comment_block or stripped.startswith('//'):
            output.append(original_line)
            continue

        # 更新类大括号计数
        if class_braces:
            open_braces = line.count('{')
            close_braces = line.count('}')
            
            # 处理开括号
            for _ in range(open_braces):
                class_braces[-1] += 1
            
            # 处理闭括号
            for _ in range(close_braces):
                if class_braces[-1] > 0:
                    class_braces[-1] -= 1
                if class_braces[-1] == 0:
                    class_braces.pop()
        
        # 检测类定义
        if class_pattern.match(stripped):
            class_braces.append(0)  # 初始计数器，遇到{时+1
        
        # 检测方法注解
        if stripped.startswith('@'):
            anno = stripped[1:].split('(')[0].strip()
            # if anno in helper_annotations:
            #     current_annotations.append(anno)
            current_annotations.append(anno)
            output.append(original_line)
            continue
            
            # # CY: 特殊处理一下：判断是否在内部类中
            # in_inner_class = len(class_braces) > 0
            # if not in_inner_class:
            #     continue

        # 方法检测逻辑
        method_match = method_pattern.match(stripped)
        if method_match and not in_method:
            # 判断是否在内部类中
            in_inner_class = len(class_braces) > 0
            
            # 内部类方法直接保留
            if in_inner_class:
                retain_current = True
            else:
                method_name = method_match.group(2)
                retain_current = (method_name == target_method_name) or \
                                (not only_keep_target_method and 
                                 any(a in helper_annotations for a in current_annotations))
            if not lines[idx-1].strip().startswith("@"): # CY: 保留， 说明没有annotations，是helper method 说明不是Tests
                retain_current = True
            
            # 初始化方法跟踪
            in_method = True
            brace_count = line.count('{') - line.count('}')
            current_annotations = []
            method_start_idx = len(output) if not retain_current else -1
            
            output.append(original_line)
            continue

        # 处理方法体内内容
        if in_method:
            brace_count += line.count('{') - line.count('}')
            
            # 方法结束
            if brace_count <= 0:
                in_method = False
                # 需要注释且不是内部类方法
                if method_start_idx != -1 and len(class_braces) == 0:
                    # CY: 注释开头的@Test, CY加的
                    if output[method_start_idx-1].strip().startswith("@"):
                        output[method_start_idx-1] = '// ' + output[method_start_idx-1]
                    if output[method_start_idx-2].strip().startswith("@"):
                        output[method_start_idx-2] = '// ' + output[method_start_idx-2]
                        
                    for i in range(method_start_idx, len(output)):
                        output[i] = '// ' + output[i]
                    output.append('// ' + original_line)
                else:
                    output.append(original_line)
                method_start_idx = -1
            else:
                output.append(original_line)
        else:
            output.append(original_line)

    return '\n'.join(output)
    
    
# previous version： 我自己手写版本。。。会有bug，没处理特殊情况
def comment_target_method(test_class_text, target_method_name, only_keep_target_method=False, keep_helper_methods=True):
    """
    Comment out methods in a Java class file, except for the target method.
    
    Args:
        test_class_text (str): The content of the Java class file.
        target_method_name (str): The name of the method to keep uncommented.
        only_keep_target_method (bool): If True, only the target method is uncommented.
        keep_helper_methods (bool): If True, helper methods with specific annotations are not commented out.
    
    Returns:
        str: The updated Java class content with methods commented out as specified.
    """
    # Parse the file using javalang
    java_class = test_class_text
    # # Parse the file using javalang
    # print( "java_class: ", java_class )
    tree = javalang.parse.parse(java_class)

    methods = []
    all_methods_start_line = []
    for path, node in tree.filter(MethodDeclaration):
        methods.append(node)
        start_line, _ = node.position
        all_methods_start_line.append(start_line)

    # Remove the irrelevant test methods line by line
    lines = java_class.splitlines()
    commented_ATTest_lines_index = []
    for method in methods:
        if only_keep_target_method:
            if method.name == target_method_name:
                continue
        else:
            if method.name != target_method_name:
                continue

        start_line, _ = method.position
        index = start_line-1 # 从当前行开始删除
        if lines[start_line-2].strip().startswith("@"):
            # keep_helper_methods
            if keep_helper_methods:
                flag_is_helper_method = False
                for ele in Junit_helper_methods_annotations:
                    if ele in lines[start_line-2]: 
                        flag_is_helper_method=True;break;
                if flag_is_helper_method: continue

            lines[start_line-2] = "// " + lines[start_line-2]  # 从@Test开始注释   
            commented_ATTest_lines_index.append(start_line-2)    # commented line index of "@Test" 
        while index<len(lines):
            lines[index] = "// " + lines[index]
            index += 1
            if index >= len(lines): 
                print("ERROR: comment_target_method, index out of range: ", index, len(lines), "target_method_name", target_method_name)
                break # 不知为啥需要这一行 。。。 20250305， 说是：： lines[index] IndexError: list index out of range
            # 说明遇到下一个method的开始了
            if index >= start_line and ( index+1 in all_methods_start_line or # 因为index是从0开始的， line number 是从1开始的
                                        lines[index].strip().startswith("@") or 
                                        lines[index].strip().startswith("public") or 
                                        lines[index].strip().startswith("void") or 
                                        lines[index]==("}") or
                                        (lines[index].strip()==("}") and index==len(lines)-1) or # 防止最后一行是 "  }"
                                        " class " in lines[index]): # # or "class " in lines[index].strip()
                break
    
    # # delete the commented @Test line, 防止给后续处理带来误报。。。
    # for line_index in commented_ATTest_lines_index:
    #     lines[line_index] = ""

    updated_java_class = "\n".join(lines)
    return updated_java_class


def comment_faulty_code(source_code: str, compilation_log: str) -> str:
    """ 
    Comment out faulty test methods and imports in the given source code.
    """
    # Identify problematic test methods
    test_methods = re.findall(r'\b@Test\b\s+public\s+void\s+(\w+)\s*\(', source_code)
    faulty_tests = set()
    
    for method in test_methods:
        if method in compilation_log:
            faulty_tests.add(method)
    
    # Identify problematic imports
    import_statements = re.findall(r'(^import\s+[^;]+;)', source_code, re.MULTILINE)
    faulty_imports = set()
    
    for imp in import_statements:
        if any(pkg in compilation_log for pkg in imp.split()):
            faulty_imports.add(imp)
    
    # Comment out faulty test methods
    for method in faulty_tests:
        source_code = re.sub(
            rf'(\b@Test\b\s+public\s+void\s+{method}\s*\(.*?\{{)',
            r'// \1',
            source_code,
            flags=re.DOTALL
        )
    
    # Comment out faulty imports
    for imp in faulty_imports:
        source_code = source_code.replace(imp, f'// {imp}')
    
    return source_code


def comment_faulty_test_cases(source_code, compilation_log):
    lines = source_code.split('\n')
    error_line_numbers = parse_compilation_log(compilation_log)
    test_methods = find_test_methods(lines)
    
    import_errors = set()
    test_methods_to_comment = set()
    
    for line_number in error_line_numbers:
        idx = line_number - 1  # Convert to 0-based index
        if idx < 0 or idx >= len(lines):
            continue
        line_content = lines[idx].strip()
        
        if line_content.startswith('import'):
            import_errors.add(idx)
        else:
            for method in test_methods:
                if method['start'] <= idx <= method['end']:
                    test_methods_to_comment.add((method['start'], method['end']))
                    break
    
    # Comment import lines
    for idx in import_errors:
        lines[idx] = '// ' + lines[idx]
    
    # Comment test methods, starting from the end to avoid shifting issues
    for start, end in sorted(test_methods_to_comment, key=lambda x: x[0], reverse=True):
        for i in range(start, end + 1):
            if i < len(lines):
                lines[i] = '// ' + lines[i]
        # cy: 特殊处理一下：annotations...
        for i in range(1, 4):
            if start-i>0 and lines[start-i].strip().startswith('@'): 
                lines[start-i] = '// ' + lines[start-i]
    
    return '\n'.join(lines)

def parse_compilation_log(log):
    line_numbers = []
    pattern = r":(\d+): error:"
    for line in log.split('\n'):
        match = re.search(pattern, line)
        if match:
            line_number = int(match.group(1))
            line_numbers.append(line_number)
    return line_numbers

def find_test_methods(lines):
    methods = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('@Test'):
            method_start = None
            # Check if current line has method signature
            if 'void test' in lines[i]:
                method_start = i
            else:
                # Look ahead for method signature
                for j in range(i + 1, len(lines)):
                    if 'void test' in lines[j]:
                        method_start = j
                        i = j  # Move index to the method start
                        break
                if method_start is None:
                    i += 1
                    continue
            # Now track braces to find method end
            brace_count = 0
            method_end = None
            for j in range(method_start, len(lines)):
                stripped_line = lines[j].strip()
                brace_count += stripped_line.count('{')
                brace_count -= stripped_line.count('}')
                if brace_count == 0:
                    method_end = j
                    break
            if method_end is not None:
                methods.append({'start': method_start, 'end': method_end})
                i = method_end  # Continue from end of method
            else:
                # Unclosed brace, skip
                pass
        i += 1
    return methods



# """ get method content """
# def get_method_content(Path_Test_file, method_signature):
#     """
#     Get the content of a specific method from a Java file.
    
#     Args:
#         Path_Test_file (str): Path to the Java file
#         method_signature (str): Method signature to find (e.g., "testMethod" or "testMethod()")
        
#     Returns:
#         str: Content of the method if found, None otherwise
#     """
#     try:
#         # Read the file content
#         with open(Path_Test_file, 'r', encoding='utf-8') as file:
#             content = file.read()
#             lines = content.split('\n')
        
#         # Clean method signature (remove parentheses if present)
#         method_name = method_signature.split('(')[0].split(' ')[-1]
        
#         # Parse the Java code
#         tree = javalang.parse.parse(content)
        
#         # Find the target method
#         for path, node in tree.filter(javalang.tree.MethodDeclaration):
#             if node.name == method_name:
#                 if not hasattr(node, 'position') or not node.position:
#                     continue
                
#                 start_line, start_col = node.position
                
#                 # Find the method body's start and end
#                 brace_count = 0
#                 body_start = None
#                 body_end = None
                
#                 # Find the opening brace of method body
#                 for i in range(start_line - 1, len(lines)):
#                     if '{' in lines[i]:
#                         body_start = i
#                         brace_count = 1
#                         # Continue counting braces until we find the matching closing brace
#                         for j in range(i + 1, len(lines)):
#                             brace_count += lines[j].count('{')
#                             brace_count -= lines[j].count('}')
#                             if brace_count == 0:
#                                 body_end = j
#                                 break
#                         break
                
#                 if body_start is not None and body_end is not None:
#                     # Include method declaration and annotations
#                     method_start = start_line - 1
#                     # Look for annotations above the method
#                     for k in range(start_line - 2, -1, -1):
#                         if lines[k].strip().startswith('@'):
#                             method_start = k
#                         elif not lines[k].strip():
#                             continue
#                         else:
#                             break
                    
#                     # Extract the complete method content including annotations
#                     method_content = '\n'.join(lines[method_start:body_end + 1])
#                     return method_content
        
#         return None
        
#     except Exception as e:
#         print(f"Error processing file {Path_Test_file}: {str(e)}")
#         return None



""" BELOW: java test results analysis """
def analyze_test_exe_result(Path_output_of_run_Test, Path_Test_file=False, FullyQuilfiedName_targetAutoMRMethod=False, assertionLineNums=False, junit_type=4):
    print("LOG: analyze_test_exe_result", Path_output_of_run_Test, Path_Test_file, FullyQuilfiedName_targetAutoMRMethod, assertionLineNums, junit_type)
    
    if junit_type == 5:
        return analyze_junit5_test_results(Path_output_of_run_Test, Path_Test_file, FullyQuilfiedName_targetAutoMRMethod, assertionLineNums)

    all_test_method_name = []
    if Path_Test_file:
        if not file_processing.pathExist(Path_Test_file):
            print("ERROR: analyze_test_exe_result, test file does not exist: ", Path_Test_file)
        else:
            test_file_content = file_processing.read_TXTfile(path=Path_Test_file)
            # 针对：ES generated test cases
            all_test_method_list = re.findall(r'void test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', test_file_content)
            for test_method in all_test_method_list:
                test_method_name = re.findall(r'test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', test_method )[0].split('(')[0]
                all_test_method_name.append(test_method_name)
            # 针对：original developer written test cases
            if len(all_test_method_name) == 0:
                all_test_method_list = re.findall(r'void [0-9_a-zA-Z]*\(\)', test_file_content)
                for test_method in all_test_method_list:
                    test_method_name = re.findall(r'[0-9_a-zA-Z]*\(\)', test_method )[0].split('(')[0]
                    all_test_method_name.append(test_method_name)

            # check if the line with the test method name startswith("//"), discard
            for line in test_file_content.split("\n"):
                if " void " in line and "// " in line: #  说明，有可能是method declaration line
                    if line.strip().startswith("//"):
                        if re.findall(r'[0-9_a-zA-Z]*\(\)', line ) and len(re.findall(r'[0-9_a-zA-Z]*\(\)', line ))>0:
                            try:
                                test_method_name = re.findall(r'[0-9_a-zA-Z]*\(\)', line )[0].split('(')[0]
                                if test_method_name in all_test_method_name:
                                    all_test_method_name.remove(test_method_name)
                            except Exception as e:
                                print("ERROR: analyze_test_exe_result", Path_Test_file, line, e)
                                continue

    output_content = file_processing.read_TXTfile(path=Path_output_of_run_Test)
    """
    正则表达式： *: 可能为0次，+：至少一次
    r'There was [0-9]* failure:'
    r'[0-9]*\) test[0-9]*\([0-9a-zA-Z._]*\)'
    r'Tests run: [0-9]*,  Failures: [0-9]*'
    r'OK \([0-9]* tests\)'
    """

    result = {"num_of_test_cases":0, "num_of_passed_test_cases":0, "num_of_assertion_failed_test_cases":0, "num_of_exception_thrown_test_cases":0, "num_of_reach_assertion_test_cases":-1, "assertionLineNums":[],
    "reach_assertion_test_cases_list":[],
    "assertion_failed_test_cases_list":[], "exception_thrown_test_cases_list":[], "passed_test_cases_list":[], "failure_info":{}}
    # 针对initializationError
    if "Tests run: 1,  Failures: 1" in output_content and " initializationError(" in output_content:
        return result
    # 针对testclass not found时
    if "Tests run: 1,  Failures: 1" in output_content and "java.lang.IllegalArgumentException: Could not find class" in output_content:
        return result
    # 针对testclass not found时
    if "OK (0 tests)" in output_content and "Could not find class:" in output_content:
        return result
    # 针对无meaningful test inputs时 / 
    if "Tests run: 1,  Failures: 1" in output_content and "No runnable methods" in output_content:
        return result
    if 'Exception in thread "main" java.lang.' in output_content:
        return result
    if len(output_content.split('\n'))<5:
        return result
    
    # # 针对运行较慢的情况
    # if "OK" not in output_content and "Tests run: " not in output_content and len(output_content.split("\n"))==2:
    #     time.sleep(30);print("sleep 30s in analyze_test_exe_result")
    #     return analyze_test_exe_result(Path_output_of_run_Test, Path_Test_file)

    exception_thrown_test_cases_list = []
    assertion_failed_test_cases_list = []
    passed_test_cases_list = []
    reach_assertion_test_cases_list = []
    # 判断结果
    ok_pattern = re.compile(r'OK \([0-9]+ test[s]*\)')
    ok_pattern_res = ok_pattern.search(output_content)
    ok_pattern2 = re.compile(r'OK\[[a-zA-Z-@/ ]*\]#  \([0-9]+ test[s]*\)') # OK[runtime@skinny-dewey /]#  (1 test)
    ok_pattern2_res = ok_pattern2.search(output_content)
    if ok_pattern_res!=None or ok_pattern2_res!=None: # 就说明全通过啊
        # 解析数量。
        num_pattern_res = re.search(r'\d+', ok_pattern_res.group())
        num_of_test_cases = int( num_pattern_res.group() )
        num_of_failed_test_cases = 0
        failure_info = {}
        passed_test_cases_list = all_test_method_name
    else: #说明有没通过的哇，解析失败和成功的数量及 failed testname
        failure_pattern = re.compile(r'Tests run: [0-9]*,  Failures: [0-9]*')
        failure_pattern_res = failure_pattern.search(output_content) # search 只匹配第一个。。。
        if failure_pattern_res==None:
            print("ERROR: analyze_test_exe_result, no failure pattern found: ", Path_output_of_run_Test)
            return result
        # 解析数量。
        num_pattern_res_list = re.findall(r'\d+', failure_pattern_res.group()) # findall 匹配多个个。。。
        num_of_test_cases = int( num_pattern_res_list[0] )
        num_of_failed_test_cases = int( num_pattern_res_list[1] )
        # print( num_of_test_cases, num_of_failed_test_cases)
        failure_info = {}
        # previous: for ES test?
        failure_test_str_list = re.findall(r'[0-9]*\) test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', output_content)
        for failed_test in failure_test_str_list:
            test_method_name = re.findall(r'test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', failed_test )[0].split('(')[0]
            if test_method_name not in failure_info: failure_info[test_method_name] = test_method_name
        # for common test
        failure_test_str_list = re.findall(r'[0-9]*\) [0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', output_content)
        for failed_test in failure_test_str_list:
            test_method_name = re.findall(r'[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', failed_test )[0].split('(')[0]
            if test_method_name not in failure_info: failure_info[test_method_name] = test_method_name
        

        # calculate the exception types, line number
        lines = output_content.split("\n")
        for line_index in range(len(lines)):
            line = lines[line_index]
            if len(re.findall(r'[0-9]*\) test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', line ))>0: # 说明是 test log start line
                test_method_name = re.findall(r'test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', line )[0].split('(')[0]
                exception_message_line = lines[line_index+1]
                exception_message = exception_message_line.split(":")[0]
                
                # exception line number
                exception_line_number = None
                for potential_exception_info_line_index in range(line_index+1, len(lines)):
                    potential_exception_info_line = lines[potential_exception_info_line_index]
                    if len(re.findall(r'[0-9]*\) test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', potential_exception_info_line ))>0: # 说明是 test log start line; 到了下一个 test的结果
                        break
                    if FullyQuilfiedName_targetAutoMRMethod and (FullyQuilfiedName_targetAutoMRMethod in potential_exception_info_line and ".java" in potential_exception_info_line): # AutoMR method invocation line
                        exception_line_number = int(potential_exception_info_line.split(".java:")[1].split(")")[0])
                        break
                # at org.cornutum.tcases.util.ObjectUtilsTest_toExternalObject_whenDecimal_AutoMR.toExternalObject_whenDecimal_AutoMR(ObjectUtilsTest_toExternalObject_whenDecimal_AutoMR.java:15)

                # # identify reach assertion test case: 1. exception line number > max(assertion lines) OR 2. exception line number = someOne(assertion lines) , & assertionError
                # if exception_line_number:
                #     if exception_line_number > max(assertionLineNums) or (exception_line_number in assertionLineNums and exception_message in config.ASSERTION_FAILURE_LIST):
                #         reach_assertion_test_cases_list.append(test_method_name)
                # identify reach assertion test case: 2. exception line number = someOne(assertion lines) , & assertionError
                if exception_line_number:
                    # assertfailed
                    # if (exception_line_number in assertionLineNums and exception_message in config.ASSERTION_FAILURE_LIST):
                    if (exception_line_number <= max(assertionLineNums) and exception_message in config.ASSERTION_FAILURE_LIST): 
                        reach_assertion_test_cases_list.append(test_method_name)
                
                # store info
                if exception_message in config.ASSERTION_FAILURE_LIST:
                    assertion_failed_test_cases_list.append( test_method_name )
                failure_info[test_method_name] = f"{exception_message}, line:{exception_line_number}" # to update
        
        passed_test_cases_list = [ ele for ele in all_test_method_name if ele not in failure_info.keys()]
        exception_thrown_test_cases_list = [ ele for ele in failure_info.keys() if ele not in assertion_failed_test_cases_list]
        reach_assertion_test_cases_list.extend(passed_test_cases_list)
        reach_assertion_test_cases_list = sorted(set(reach_assertion_test_cases_list))
    
    assertion_failed_test_cases_list = list( set(assertion_failed_test_cases_list) )
    exception_thrown_test_cases_list = list( set(exception_thrown_test_cases_list) )
    # result['num_of_test_cases']= num_of_test_cases 
    if num_of_test_cases < len(all_test_method_name):
        num_of_test_cases = len(all_test_method_name)
    result['num_of_test_cases']= num_of_test_cases
    result['num_of_assertion_failed_test_cases']= len(assertion_failed_test_cases_list) 
    result['num_of_exception_thrown_test_cases']= num_of_failed_test_cases - len(assertion_failed_test_cases_list)
    result['num_of_passed_test_cases']= num_of_test_cases - num_of_failed_test_cases 
    result['num_of_reach_assertion_test_cases']= len(reach_assertion_test_cases_list) 
    result['assertionLineNums']= assertionLineNums
    result['reach_assertion_test_cases_list']= reach_assertion_test_cases_list 
    result['assertion_failed_test_cases_list']= assertion_failed_test_cases_list 
    if result['num_of_passed_test_cases']>0:
        result['passed_test_cases_list']= passed_test_cases_list 
    result['exception_thrown_test_cases_list']= exception_thrown_test_cases_list 
    result['failure_info']= failure_info 
    return result

def analyze_junit5_test_results(Path_output_of_run_Test, Path_Test_file=False, FullyQuilfiedName_targetAutoMRMethod=False, assertionLineNums=False):
    print("LOG: analyze_junit5_test_results", Path_output_of_run_Test, Path_Test_file, FullyQuilfiedName_targetAutoMRMethod, assertionLineNums)
    output_content = file_processing.read_TXTfile(path=Path_output_of_run_Test)
    all_test_method_name = []
    if Path_Test_file:
        if not file_processing.pathExist(Path_Test_file):
            print("ERROR: analyze_test_exe_result, test file does not exist: ", Path_Test_file)
        else:
            test_file_content = file_processing.read_TXTfile(path=Path_Test_file)
            # 针对：ES generated test cases
            all_test_method_list = re.findall(r'void test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', test_file_content)
            for test_method in all_test_method_list:
                test_method_name = re.findall(r'test[0-9_a-zA-Z]*\([0-9a-zA-Z._]*\)', test_method )[0].split('(')[0]
                all_test_method_name.append(test_method_name)
            # 针对：original developer written test cases
            if len(all_test_method_name) == 0:
                all_test_method_list = re.findall(r'void [0-9_a-zA-Z]*\(\)', test_file_content)
                for test_method in all_test_method_list:
                    test_method_name = re.findall(r'[0-9_a-zA-Z]*\(\)', test_method )[0].split('(')[0]
                    all_test_method_name.append(test_method_name)
            # check if the line with the test method name startswith("//"), discard
            for line in test_file_content.split("\n"):
                if " void " in line and "// " in line: #  说明，有可能是method declaration line
                    if line.strip().startswith("//"):
                        try:
                            test_method_name = re.findall(r'[0-9_a-zA-Z]*\(\)', line )[0].split('(')[0]
                            if test_method_name in all_test_method_name:
                                all_test_method_name.remove(test_method_name)
                        except Exception as e:
                            # print the file, line, and exception message
                            print("ERROR: analyze_junit5_test_results", Path_Test_file, line, e)
                            continue

    result = {
        "num_of_test_cases": 0,
        "num_of_passed_test_cases": 0,
        "num_of_assertion_failed_test_cases":0, 
        "num_of_exception_thrown_test_cases":0, 
        "num_of_reach_assertion_test_cases": -1, 
        "assertionLineNums": [],
        "reach_assertion_test_cases_list":[],
        "assertion_failed_test_cases_list":[], 
        "exception_thrown_test_cases_list":[], 
        "passed_test_cases_list":[], 
        "failure_info":{}
    }

    # Parse general test run info
    test_run_info_pattern = r'\[.*?\]'
    test_run_info_matches = re.findall(test_run_info_pattern, output_content)
    exe_result = {}
    for info in test_run_info_matches:
        # [         1 tests started         ]
        if " tests " not in info: continue
        value, tests, key = [s.strip() for s in info.strip('[]').strip(' ').split(' ')]
        if tests == "tests":
            exe_result[key] = int(value)

    # Update result with total tests and total successful tests
    result['num_of_test_cases'] = exe_result.get('found', 0)
    result['num_of_passed_test_cases'] = exe_result.get('successful', 0)
    # result['num_of_failed_test_cases'] = exe_result.get('failed', 0)

    # Parse failed tests
    failed_test_pattern = r'(JUnit\sJupiter:.+?\n\s+MethodSource.+\n\s+=>\s+.+)'
    failed_tests_matches = re.findall(failed_test_pattern, output_content)
    for failed_test in failed_tests_matches:
        """
        failed_test JUnit Jupiter:ExecutionTest:test_equals()
        MethodSource [className = 'com.github.kagkarlsson.scheduler.ExecutionTest', methodName = 'test_equals', methodParameterTypes = '']
        => org.opentest4j.AssertionFailedError: expected: <1> but was: <2>
        """
        if "methodName = " not in failed_test: 
            print("ERROR: analyze_junit5_test_results", Path_output_of_run_Test,Path_Test_file)
            continue

        test_name = re.search(r"methodName = '([^']+)'" , failed_test).group(1)
        exception_message_line = re.search(r'=>\s(.+)', failed_test).group(1)
        exception_message = exception_message_line.split(":")[0]
        # print("exception_message", exception_message)
        if exception_message in config.ASSERTION_FAILURE_LIST:
            result['assertion_failed_test_cases_list'].append(test_name)
        else:
            result['exception_thrown_test_cases_list'].append(test_name)
        result['failure_info'][test_name] = exception_message_line

    # Determine passed tests
    if result['num_of_passed_test_cases'] > 0: 
        result['passed_test_cases_list'] = [test for test in all_test_method_name if test not in result['assertion_failed_test_cases_list'] and test not in result['exception_thrown_test_cases_list']]

    result['num_of_assertion_failed_test_cases'] = len( result['assertion_failed_test_cases_list'] )
    result['num_of_exception_thrown_test_cases'] = len( result['exception_thrown_test_cases_list'] )

    return result


def getMethodBasedOnMethodSignature(class_path, method_signature_formated):
    """
    Extract a method from a Java class file based on its signature.
    
    Args:
        class_path:
        method_signature_formated: Method signature in format "{return_type}:{method_name}:{parameter_simple_types}". return_type can be "NA" or anything
        
    Returns:
        str: The method code as a string, or empty string if not found
        
    Example:
        method_signature_formated = "String:setPackages:String"
        This will find a method with:
        - return type: String
        - method name: setPackages  
        - parameter type: String
    """
    function = "getMethodBasedOnMethodSignature"
    try:
        # Read the Java file
        with open(class_path, 'r', encoding='utf-8') as f:
            java_code = f.read()
        
        # Parse the method signature
        parts = method_signature_formated.split(':')
        if len(parts) != 3:
            print(f"ERROR: {function}, invalid method signature format: {method_signature_formated}")
            return ""
        
        return_type, method_name, parameter_types = parts
        # format
        parameter_types_str = parameter_types.strip(" ")
        expected_params = [] 
        for param in parameter_types_str.split(","):
            if ">" in param and "<" not in param: continue # , String>) from (String, ConnectionType, Map<String, String>)
            formatted_param = param.strip()
            formatted_param = formatted_param.split("<")[0] # Class<T> -> Class
            expected_params.append(formatted_param) # (OboFormatTag,Class<T>)

        # print("method_name", method_name, "parameter_types", parameter_types)
        
        # Parse the Java code using javalang
        tree = javalang.parse.parse(java_code)
        
        # Find the method with matching signature
        for path, node in itertools.chain(tree.filter((javalang.tree.MethodDeclaration)), tree.filter((javalang.tree.ConstructorDeclaration))):
            if node.name == method_name:
                print("node.name", node.name)
                # # Check return type (skip if return_type is "NA" or empty)
                # if return_type and return_type != "NA":
                #     actual_return_type = node.return_type.name if node.return_type else "void"
                #     if actual_return_type != return_type:
                #         continue
                
                # Check parameter types
                if parameter_types and parameter_types != "NA":
                    # expected_params = [p.strip() for p in parameter_types.split(',') if p.strip()] # (OboFormatTag,Class<T>)
                    actual_params = [] # (OboFormatTag, Class)
                    
                    if node.parameters:
                        for param in node.parameters:
                            param_type = param.type.name if param.type else "void" # is just a simple name like "Class"/"char" rather than "Class<T>"/"char[]"
                        
                            # handle java.lang.String -> String
                            if hasattr(param.type, 'sub_type') and param.type.sub_type:
                                param_type = param.type.sub_type.name
                                if hasattr(param.type.sub_type, 'sub_type') and param.type.sub_type.sub_type:
                                    param_type = param.type.sub_type.sub_type.name
                                    if hasattr(param.type.sub_type.sub_type, 'sub_type') and param.type.sub_type.sub_type.sub_type:
                                        param_type = param.type.sub_type.sub_type.sub_type.name
                                        if hasattr(param.type.sub_type.sub_type, 'sub_type') and param.type.sub_type.sub_type.sub_type:
                                            param_type = param.type.sub_type.sub_type.sub_type.name
                            # Handle array dimensions
                            if hasattr(param.type, 'dimensions') and param.type.dimensions:
                                param_type += '[]' * len(param.type.dimensions)
                                
                            if hasattr(param.type, 'arguments') and param.type.arguments: 
                                # Handle generic type arguments
                                type_args = []
                                for arg in param.type.arguments:
                                    if hasattr(arg, 'name'):
                                        type_args.append(arg.name)
                                    elif hasattr(arg, 'type') and hasattr(arg.type, 'name'):
                                        type_args.append(arg.type.name)
                                    else:
                                        type_args.append(str(arg))
                                if type_args:
                                    param_type += f"<{','.join(type_args)}>"
                            
                            param_type = param_type.split("<")[0] # 算了，一切从简吧：
                            
                            actual_params.append(param_type)
                    
                    
                    # expected_params ['Class<?>', 'String'] actual_params ['Class<TypeArgument(pattern_type=?, type=None)>', 'String']
                    
                    # Simple parameter matching (just check count and simple names)
                    if len(expected_params) != len(actual_params):
                        continue
                    
                    # Check if parameter types match (simple name comparison)
                    params_match = True
                    print("method_name", method_name, "parameter_types", parameter_types)
                    print("expected_params", expected_params, "actual_params", actual_params)
                    for expected, actual in zip(expected_params, actual_params):
                        # Extract simple name (last part after dot)
                        expected_simple = expected.split('.')[-1]
                        actual_simple = actual.split('.')[-1]
                        if expected_simple != actual_simple:
                            params_match = False
                            break
                    
                    if not params_match:
                        continue
                
                # Found matching method, extract its code
                start_line = node.position.line if node.position else 1
                end_line = start_line
                
                lines = java_code.split('\n')
                # Count lines in the method body
                if node.body:
                    # version: 1
                    last_stmt = node.body[-1]
                    # Find the last line of the last statement
                    end_line = last_stmt.position.line
                    
                    # # version: 2
                    # method_str = str(node)
                    # end_line = start_line + method_str.count('\n')
                
                # Extract the method code from the file
                method_lines = lines[start_line - 1:end_line+1]  # -1 because line numbers start from 1
                method_code = '\n'.join(method_lines)
                
                return method_code
        
        # Method not found
        print(f"WARNING: {function}, method not found: {method_signature_formated}", class_path)
        return ""
        
    except Exception as e:
        print(f"ERROR: {function}, error parsing Java file {class_path}: {e}")
        # print the error traceback
        traceback.print_exc()
        
        return ""

def get_simpleMethodName_simpleParameterTypes_from_methodFQS(method_FQS):
    # org.semanticweb.owlapi.model.OWLOntologyManager.createOntology(java.util.Collection<org.semanticweb.owlapi.model.OWLAxiom>, org.semanticweb.owlapi.model.IRI
    print("method_FQS", method_FQS)
    
    method_FQN = method_FQS.split("(")[0]
    # method name
    method_name = method_FQN.split(".")[-1]
    # parameter types
    parameter_str = method_FQS.split("(")[1].split(")")[0]
    
    parameter_types = []
    for param in parameter_str.split(","):
        formatted_param = param.strip()
        formatted_param = formatted_param.split(" ")[0] # in case of ""
        # java.util.Collection<org.semanticweb.owlapi.model.OWLAxiom> -> Collection<OWLAxiom>
        if "<" in formatted_param:
            param_type = f"{formatted_param.split('<')[0].split('.')[-1]}<{formatted_param.split('<')[1].split('>')[0].split('.')[-1]}>"
        else:
            param_type = formatted_param.split(".")[-1]
        parameter_types.append(param_type)
    
    simple_parameter_types = ",".join(parameter_types)
    return method_name, simple_parameter_types


def get_classPath_methodCode_returnType(method_FQS, poj_dir):
    print("get_classPath_methodCode_returnType(method_FQS, poj_dir)", method_FQS, poj_dir)
    class_path = find_class_file_path_by_methodFQS(poj_dir, method_FQS)
    return_type = ""
    
    method_name, parameter_simple_types = get_simpleMethodName_simpleParameterTypes_from_methodFQS(method_FQS)
    method_signature_formated = f"{return_type}:{method_name}:{parameter_simple_types}"
    
    MUT_code = getMethodBasedOnMethodSignature(class_path, method_signature_formated)
    # get more precise return_type 
    return_type = java_parser._get_precise_return_type(MUT_code, method_name)
    if return_type == "empty": return_type = ""
    
    return class_path, MUT_code, return_type