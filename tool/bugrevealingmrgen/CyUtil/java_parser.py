#!/usr/bin/env python
# encoding: utf-8
"""

Created on 2019/10/16 12:27
@Author : 


# https://github.com/c2nes/javalang
"""

# import pathlib


# # Replace 'YourJavaFile.java' with your actual file path.
# find_asserts_in_java_file('YourJavaFile.java')


import json, os, sys
_PROJECT_NAME = "CyUtil"
_CURRENT_ABSPATH = os.path.abspath(__file__)
sys.path.insert(0, _CURRENT_ABSPATH[:_CURRENT_ABSPATH.find(_PROJECT_NAME) + len(_PROJECT_NAME) + 1])
# from utility import file_processing, json_processing, CSV_processing, data_propcessing, java_parser
import config
import random
import javalang

import subprocess

# def get_method_code(java_file="", method_name="", class_code=""):
#     source_code = class_code
#     # Read the Java file
#     if len(java_file)>0:
#         with open(java_file, 'r') as file:
#             source_code = file.read()

#     # Parse the Java code
#     tree = javalang.parse.parse(source_code)

#     # Find the method with the given name
#     for path, node in tree:
#         if isinstance(node, javalang.tree.MethodDeclaration):
#             # Check if the method name matches either the simple name or the fully-qualified name
#             # print(node.name)
#             if node.name == method_name:
#                 # Get the code of the method
#                 start_line = node.position.line
#                 method_length = len(node.body)

#                 end_line = start_line + method_length 
#                 end_line_index = -1
#                 for index in range( end_line+1, len(source_code.split('\n')) ):
#                     line =  source_code.split('\n')[index]
#                     if line == ("}") or  (" public ") in line or (" void ") in line :
#                         break
#                     if line == ("    }") or line == ("  }"):
#                         end_line_index = index
#                         end_line = index
#                         break
#                 # end_line = start_line + method_length if start_line + method_length > end_line_index else end_line_index
#                 method_code = source_code.split('\n')[start_line-1:end_line +1]
#                 # method_code = source_code[node.position.start.offset:node.position.end.offset]
#                 return '\n'.join(method_code)
#                 # method_code = node.body.__str__
#                 # return method_code

#     # If method is not found, return None
#     return None


def get_method_content(java_file_path, method_name, class_code):
    java_code = class_code
    if len(java_file_path) > 0:
        with open(java_file_path, 'r') as java_file:
            java_code = java_file.read()

    tree = javalang.parse.parse(java_code)
    for path, node in tree.filter(javalang.tree.MethodDeclaration):
        if node.name == method_name:
            # print(node)
            # return node
            start_line = node.position.line
            end_line = start_line + str(node).count('\n')
            lines = java_code.split('\n')
            return '\n'.join(lines[start_line - 1 : end_line])  # -1 because line numbers start from 1

def replace_method(file_path, method_name, new_method_declaration, function):
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path, method_name, new_method_declaration], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')

def get_skeleton_of_class(file_path, function):
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')

def getDeclaredMethodsAndConstructors(file_path, function):
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path], stdout=subprocess.PIPE)
    all_methods_info_str = result.stdout.decode('utf-8').replace("\n","").rstrip(';')
    all_methods_info = all_methods_info_str.split(';')
    
    all_methods_info_formal = {}
    for method_info in all_methods_info:
        if method_info != "":
            return_type = method_info.split(':')[0]
            name = method_info.split(':')[1]
            params = method_info.split(':')[2].replace("void","")
            method_sig = f"{name}({params})"
            all_methods_info_formal[method_info] = {
                "return_type": return_type,
                "name": name,
                "params": params,
                "method_sig": method_sig
            }
    return all_methods_info_formal


def getInvokedMethodsInaMethod(file_path, formattedMethodName ,function):
    # formattedMethodName: "void: setHref:String,String"
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path, formattedMethodName], stdout=subprocess.PIPE)
    json_str =  result.stdout.decode('utf-8')
    if len(json_str) == 0: return None
    # print("getInvokedMethodsInaMethod json_str: ", json_str)
    try: 
        result_json = json.loads(json_str)
        return result_json
    except Exception as e:
        print("Error parsing JSON: %s", e)
        print("json_str: ", json_str)
        return None


def getAccessORUpdatedFiledsInaMethod(file_path, formattedMethodName ,function):
    # formattedMethodName: "void: setHref:String,String"
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path, formattedMethodName], stdout=subprocess.PIPE)
    json_str =  result.stdout.decode('utf-8')
    if len(json_str) == 0: return None
    # print("getAccessORUpdatedFiledsInaMethod json_str: ", json_str)
    try: 
        result_json = json.loads(json_str)
        return result_json
    except Exception as e:
        print("Error parsing JSON: %s", e)
        print("json_str: ", json_str)
        return None



# deprecated, use java_file_processing.getMethodBasedOnMethodSignature instead
def getMethodBasedOnMethodSignature(file_path, method_name, function):
    """
        method_name: NA:setHref:String
        
        // Parse method signature format: returnType:methodName:param1,param2,...
        // returnType can be "NA"
        // param1,param2,... can be "NA" if no parameters; param2 just "String" not "java.lang.String/a"
    """
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path, method_name], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


def getDeclaredVariablesInMethod(file_path, method_name, function):
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path, method_name], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')

def getInvolvedClassInMethod(file_path, method_name, function):
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path, method_name], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')

def getVaribleRelevantCode(file_path, method_name, variable_info, function):
    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path, method_name, variable_info], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')

def get_method_body_or_related_class_field(file_path, method_name, function):

    result = subprocess.run([config.PATH_JAVA_8, '-jar', config.AUTOMR_JAVA_DEMO_JAR_PATH , "com.hkust.castle.util.paserJavaFileUtil", function, file_path, method_name], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


def _get_precise_return_type(method_content: str, method_name: str) -> str:
    """
    Get the precise return type of a MUT.
    
    Args:
        method_content: The full content of the method including its signature
        method_name: The name of the method to find
        
    Returns:
        str: The return type of the method, or "" if not found
        
    Example:
        Input method_content: "public static String getValue(int param) { ... }"
        Input method_name: "getValue"
        Returns: "String"
    """
    try:
        # Split the content into lines and find the method declaration
        lines = method_content.split('\n')
        for line in lines:
            line = line.strip()
            # Look for the method declaration
            if f" {method_name}(" in line:
                # Remove any opening brace and parameters after method name
                signature = line.split('{')[0]  # remove everything after '{'
                before_name = signature.split(f"{method_name}(")[0].strip()
                # before_name = line.split(f"{method_name}(")[0].strip()
                tokens = before_name.split()
                
                # special case: is constructor, and no "public" or "private" or "protected"
                if before_name == "":
                    return method_name # return_type = method_name = class_name

                # Heuristic: last token before method name is the return type
                if tokens:
                    return_type = tokens[-1]
                    # special case: byte []
                    if return_type == "[]" and len(tokens) > 2: 
                        return_type = f"{tokens[-2]} {tokens[-1]}"
                    # special case: constructor, "public" or "private" or "protected"
                    if return_type in ["public", "private", "protected"]:
                        return_type = method_name
                    return return_type
        return ""  # Return empty string if not found
    except Exception as e:
        print("Error extracting return type: %s", e)
        return ""
