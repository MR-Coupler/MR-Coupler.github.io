
"""
    Patterns based on signatures of methods m1 and m2  
    
    
    (1) 1. m1 and m2 are the same method
    
        2. m1 and m2 share the same method name, but different parameters (overloading)
    (2)    2.1 m1's {parameters, return type} has the overlap with m2's
    (3)    2.2 m1's {parameters, return type} has no overlap with m2's
    
        3. m1 and m2 have different method names, but share some method name tokens (split by '_' or camelCase)
    (4)    3.1 m1's {parameters, return type} is the same set of m2's 
    (5)    3.2 m1's {parameters, return type} has the overlap with m2's
    (6)    3.3 m1's {parameters, return type} has no overlap with m2's  
    
    
        4. m1 and m2 have different method names, but share no method name tokens (split by '_' or camelCase)
    (7)    4.1 m1's {parameters, return type} is the same set of m2's 
    (8)    4.2 m1's {parameters, return type} has the overlap with m2's
    (9)    4.3 m1's {parameters, return type} has no overlap with m2's  
    

minors to update:
* whether default types are considered (String, int, ..., Class<?> )
"""

import re
import logging

from util import java_parser



# Set up logging
logger = logging.getLogger(__name__)

def setup_logging(level=logging.DEBUG):
    """
    Set up logging configuration for the module.
    
    Args:
        level: Logging level (default: logging.INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def split_camel_case(text):
    """
    Split camelCase text into tokens.
    Example: 'setPackages' -> ['set', 'Packages']
    """
    return re.findall(r'[A-Z]?[a-z]+|[A-Z]{2,}(?=[A-Z][a-z]|\b|\d)|\d+', text)

def parse_method_signature(method_signature: str, consider_empty_para_as_str: bool = True):
    """
    Parse the method signature and return the method name, parameters, and return type.
    """
    # print(f"parse_method_signature(method_signature): {method_signature}")
    # Parse the main MUT signature. 
    # example: method_signature == void setPackages(java.lang.String)
    method_name = method_signature.split('(')[0].split(' ')[-1]
    
    """ name """
    # Split method name tokens by underscore and camelCase
    simple_method_name = method_name.split('.')[-1] # in case of full-qualified name, like java.lang.String
    underscore_tokens = simple_method_name.split('_')
    camel_case_tokens = []
    for token in underscore_tokens:
        camel_case_tokens.extend(split_camel_case(token))
    # Convert to lowercase for comparison
    simple_method_name_tokens = [token.lower() for token in camel_case_tokens if token]
    
    """ parameters """
    # parameters = method_signature.split('(')[1].rstrip(')').split(',') if '(' in method_signature else []
    # simple_parameters = [param.strip().split('.')[-1] for param in parameters] # simple name
    # if "T" in simple_parameters: simple_parameters.remove("T")
    # if simple_parameters == [""]: simple_parameters = ["void"]
    
    
    
    
    parameter_str = method_signature.split("(")[1].split(")")[0]
    parameter_str_split = parameter_str.split(",")
    parameter_types = []
    parameter_elements = []
    pre_param = ""
    # for param in parameter_str_split: # to fix bug: substituteVariables(String, Map<java.lang.String, java.lang.String>)
    #     if "<" in param and ">" not in param:
    #         pre_param = param
    #         continue
    #     if ">" in param and "<" not in param:
    #         parameter_elements.append(f"{pre_param}, {param}")
    #         pre_param = ""
    #         continue
    #     parameter_elements.append(param)
    
    #     for param in parameter_elements:
    pre_param = ""
    for param in parameter_str.split(","):
        formatted_param = param.strip()
        formatted_param = formatted_param.split(" ")[0] # in case of "(ObjectMapper mapper, String baseURL, Class<?>... classes)"
        # java.util.Collection<org.semanticweb.owlapi.model.OWLAxiom> -> Collection<OWLAxiom>
        # fix bug: substituteVariables(String, Map<java.lang.String, java.lang.String>)
        if "<" in formatted_param and ">" in formatted_param:
            param_type = f"{formatted_param.split('<')[0].split('.')[-1]}<{formatted_param.split('<')[1].split('>')[0].split('.')[-1]}>"
        elif "<" in formatted_param and ">" not in formatted_param:
            param_type = f"{formatted_param.split('<')[0].split('.')[-1]}<{formatted_param.split('<')[1].split('>')[0].split('.')[-1]}"
            pre_param = param_type
            continue
        elif ">" in param and "<" not in param:
            param_type = f"{formatted_param.split('>')[0].split('.')[-1]}>"
            param_type = f"{pre_param}, {param_type}"
            pre_param = ""
        else:
            param_type = formatted_param.split(".")[-1] # simple name
        parameter_types.append(param_type)
    
    # unify the parameter types
    # if "T" in parameter_types: parameter_types.remove("T") # let still keep it...sometime, it is the only one ...
    if parameter_types == [""] and consider_empty_para_as_str: parameter_types = ["void"]  # special operation-void
    # simple_parameter_types = ",".join(parameter_types)
    
    
    """ return type """
    return_type = method_signature.split(' ')[0]
    if method_name in return_type: # in case of no return type, just "setPackages(java.lang.String)"
        return_type = "NA"
    if return_type == "": return_type = "NA"
    return_type = return_type.split('.')[-1] # simple name
    return method_name, simple_method_name_tokens, parameter_types, return_type


defined_pattern_index = ["Sig1", "Sig2.1", "Sig2.2", "Sig3.1", "Sig3.2", "Sig3.3", "Sig4.1", "Sig4.2", "Sig4.3", "MI1", "MI2", "MI3", "State1", "State2", "State3", "State4"]
strong_pattern_index = ["Sig1", "Sig2.1", "Sig2.2", "Sig3.1", "Sig3.2", "Sig4.1"] # must overlap in method&paramReturnType
# encode, decode 不在这个范围内。。还挺尴尬. + 4.1 吧。。。
strong_pattern_index += ["MI1", "MI2", "State1", "State2"] # method invocation patterns



def identify_pattens(MUT_signature: str, other_MUTs_signatures: list[str]):
    """
    Identify the pattern of paired methods in the given MUT and other MUTs.
    
    Patterns based on signatures of methods m1 and m2  
    
    
    (1) 1. m1 and m2 are the same method
    
        2. m1 and m2 share the same method name, but different parameters (overloading)
    (2)    2.1 m1's {parameters, return type} has the overlap with m2's
    (3)    2.2 m1's {parameters, return type} has no overlap with m2's
    
        3. m1 and m2 have different method names, but share some method name tokens (split by '_' or camelCase)
    (4)    3.1 m1's {parameters, return type} is the same set of m2's 
    (5)    3.2 m1's {parameters, return type} has the overlap with m2's
    (6)    3.3 m1's {parameters, return type} has no overlap with m2's  
    
    
        4. m1 and m2 have different method names, but share no method name tokens (split by '_' or camelCase)
    (7)    4.1 m1's {parameters, return type} is the same set of m2's 
    (8)    4.2 m1's {parameters, return type} has the overlap with m2's
    (9)    4.3 m1's {parameters, return type} has no overlap with m2's  

    """
    patterns = []
    # Parse the main MUT signature. 
    # example: mut_method_name == void setPackages(java.lang.String)
    mut_method_name, simple_mut_name_tokens, mut_params, mut_return_type = parse_method_signature(MUT_signature)
    mut_params_with_return = mut_params + [mut_return_type]

    for other_mut_sig in other_MUTs_signatures:
        if not other_mut_sig or len(other_mut_sig) < 3: continue # in case of empty string
        other_mut_method_name, simple_other_mut_name_tokens, other_mut_params, other_mut_return_type = parse_method_signature(other_mut_sig)
        other_mut_params_with_return = other_mut_params + [other_mut_return_type]    
        
        pattern = {
            "mut_signature": MUT_signature,
            "paired_mut_signature": other_mut_sig,
            "pattern_type": None,
            "relationship": None
        }
        
        # Convert to sets for comparison
        mut_params_with_return_set = set(mut_params_with_return)
        other_mut_params_with_return_set = set(other_mut_params_with_return)
        
        # Check for name token overlap
        name_token_overlap = bool(set(simple_mut_name_tokens) & set(simple_other_mut_name_tokens))
        paramsReturnType_overlap = len(mut_params_with_return_set & other_mut_params_with_return_set) > 0
        same_method_name = mut_method_name == other_mut_method_name
        
        logger.debug(f"MUT_signature: {MUT_signature}, other_mut_sig: {other_mut_sig}")
        logger.debug(f"mut_params_with_return_set: {mut_params_with_return_set}, other_mut_params_with_return_set: {other_mut_params_with_return_set}")
        logger.debug(f"name_token_overlap: {name_token_overlap}, paramsReturnType_overlap: {paramsReturnType_overlap}, same_method_name: {same_method_name}")
        
        # print(f"MUT_signature: '{MUT_signature}', '{other_mut_sig}'")
        # print(f"mut_method_name: {mut_method_name}, {other_mut_method_name}")
        # print(f"simple_mut_name_tokens: {simple_mut_name_tokens}, {simple_other_mut_name_tokens}")
        # print(f"mut_params_with_return_set: {mut_params_with_return_set}, {other_mut_params_with_return_set}")
        # print(f"name_token_overlap: {name_token_overlap}, paramsReturnType_overlap: {paramsReturnType_overlap}, same_method_name: {same_method_name}")
        
        # 1. Check if methods are identical
        if MUT_signature == other_mut_sig:
            pattern["pattern_type"] = 1
            pattern["relationship"] = "identical_methods"
            
        # 2. Check if methods share the same name (overloading)
        elif same_method_name:
            if paramsReturnType_overlap:  # Check for intersection
                pattern["pattern_type"] = 2.1
                pattern["relationship"] = "overloaded_methods_overlap_paramReturnType"
            else:
                pattern["pattern_type"] = 2.2
                pattern["relationship"] = "overloaded_methods_noOverlap_paramReturnType"
            
        # 3. Methods have different names, but share some method name tokens
        elif name_token_overlap:
            if mut_params_with_return_set == other_mut_params_with_return_set:
                pattern["pattern_type"] = 3.1
                pattern["relationship"] = "overlap_methodNameToken_same_paramReturnType"
            elif paramsReturnType_overlap:  # Check for intersection
                pattern["pattern_type"] = 3.2
                pattern["relationship"] = "overlap_methodNameToken_overlap_paramReturnType"
            else:
                pattern["pattern_type"] = 3.3
                pattern["relationship"] = "overlap_methodNameToken_noOverlap_paramReturnType"
                
        # 4. Methods have different names, and share no method name tokens
        else:
            if mut_params_with_return_set == other_mut_params_with_return_set:
                pattern["pattern_type"] = 4.1
                pattern["relationship"] = "different_methodName_same_paramReturnType"
            elif paramsReturnType_overlap:  # Check for intersection
                pattern["pattern_type"] = 4.2
                pattern["relationship"] = "different_methodName_overlap_paramReturnType"
            else:
                pattern["pattern_type"] = 4.3
                pattern["relationship"] = "different_methodName_noOverlap_paramReturnType"
        
        # print(f"MUT_signature: {MUT_signature}", f"mut_method_name: {mut_method_name}", f"mut_params: {mut_params_with_return}", f"mut_return_type: {mut_return_type}")
        # print(f"other_mut_sig: {other_mut_sig}", f"other_mut_method_name: {other_mut_method_name}", f"other_mut_params: {other_mut_params_with_return}", f"other_mut_return_type: {other_mut_return_type}")
        # print(f"pattern: {pattern}")
        # print("--------------------------------")
        patterns.append(pattern)
        # print(f"pattern: {pattern}")
    # in order
    patterns = sorted(patterns, key=lambda x: x["pattern_type"])
    # previous version
    # return {
    #     "given_mut_method": MUT_signature,
    #     "paired_patterns": patterns[0] if patterns else None # 暂时，只考虑一个
    # }
    
    return {
        "given_mut_method": MUT_signature,
        "paired_patterns": patterns
    }
    

def suggest_paired_methods_by_pattern(MUT_signature_w_returnType: str, class_under_test_path: str):
    """
    Suggest paired methods for the given MUT-A in the class under test.
    
    ruturn: list of method signatures        
        signature example:String org.codehaus.gmavenplus.model.LinkTest.Getters(java.lang.String)
    """
    # Get the base method information
    # change MUT_signature to the base method signature, MUT_signature: org.codehaus.gmavenplus.model.LinkTest.testGetters(java.lang.String) -> base_method: testGetters(String)
    mut_method_name, simple_mut_name_tokens, mut_simple_params, mut_return_type = parse_method_signature(MUT_signature_w_returnType)
    # TODO: if debug, uncomment this
    # print(f"mut_method_name: {mut_method_name}, simple_mut_name_tokens: {simple_mut_name_tokens}, mut_simple_params: {mut_simple_params}, mut_return_type: {mut_return_type}")
    simple_mut_method_name = mut_method_name.split('.')[-1]
    mut_method_name = simple_mut_method_name
    mut_params  = mut_simple_params
    mut_signature = f"{mut_method_name}({','.join(mut_params)})"
    mut_signature = mut_signature.replace("(void)", "()") # special operation-void

    mut_params_set = set(mut_params)
    if mut_return_type not in ["NA", "", "empty"]: 
        mut_params_return_type_set = set(mut_params + [mut_return_type])
    else: mut_params_return_type_set = mut_params_set
    # logger.info("mut_params_return_type_set: %s", len(mut_params_return_type_set))
    # logger.info("MUT_signature: %s, mut_params: %s, mut_return_type: %s", MUT_signature, mut_params, mut_return_type)
    
    # try:            
    # Simple method extraction using basic parsing
    # This could be enhanced with a proper Java parser like javalang
    # all_methods_info_str: void:main:String[];void:findFileList:File,List<String>;List<String>:findFileNameListLevel1:String;void:writeTextFile:String,String;String:readTextFile:String;boolean:folderExisting:String;void:folderExistingIfNotCreate:String;boolean:fileExisting:String;String:findPojDir:String,String;String:findPojName:String,String;void:deleteFile:String;void:deleteFilesInFolder:String;void:createFolder:String;
    logger.debug("class_under_test_path: %s", class_under_test_path)
    all_methods_info = java_parser.getDeclaredMethodsAndConstructors(class_under_test_path, "getDeclaredMethodsAndConstructors")
    logger.debug("all_methods_info: %s", all_methods_info)

    # MUT_signature = MUT_signature_w_returnType.lstrip(mut_return_type)
    MUT_signature = f"{simple_mut_method_name}({ ','.join(mut_simple_params)})"
    pattern_suggested_pairMethods_metadata = {
        "Sig1": {}, "Sig2.1": {}, "Sig2.2": {}, "Sig3.1": {}, "Sig3.2": {}, "Sig3.3": {}, "Sig4.1": {}, "Sig4.2": {}, "Sig4.3": {}
    }
    pattern_methods_dict = {
        # 1 :[MUT_signature],
        "Sig1": [], "Sig2.1": [], "Sig2.2": [], "Sig3.1": [], "Sig3.2": [], "Sig3.3": [], "Sig4.1": [], "Sig4.2": [], "Sig4.3": []
    }
    for method_info in all_methods_info:
        # print(f"method_info: {method_info}") # String:getPackages:void
        method_return_type = method_info.split(':')[0]
        method_name = method_info.split(':')[1]
        method_params = method_info.split(':')[2]
        method_sig = f"{method_name}({method_params})"
        _, method_name_tokens, method_simple_params, _ = parse_method_signature(method_sig)
        

        # Parse method parameters and create sets for comparison
        # method_params_list = method_params.split(',') if method_params else ["void"] # special operation-void
        # method_params_set = set(method_params_list)
        # method_params_return_type_set = set(method_params_list + [method_return_type])
        method_params_set = set(method_simple_params)
        method_params_return_type_set = set(method_simple_params + [method_return_type])
        
        # Check for name token overlap between MUT and current method
        same_method_name = mut_method_name == method_name
        name_token_overlap = bool(set(simple_mut_name_tokens) & set(method_name_tokens))
        params_same = mut_params_set == method_params_set
        paramsReturnType_same = mut_params_return_type_set == method_params_return_type_set
        paramsReturnType_overlap = len(mut_params_return_type_set & method_params_return_type_set) > 0
        
        method_sig = method_sig.replace("(void)", "()") # special operation-void
        # TODO: if debug, uncomment this
        # print(f"MUT_signature_w_returnType: `{MUT_signature_w_returnType}`, method_sig: `{method_sig}`, class_under_test_path: `{class_under_test_path}`")
        # print(f"mut_params_return_type_set: {mut_params_return_type_set}, method_params_return_type_set: {method_params_return_type_set}")
        if same_method_name:
            if params_same:
                pattern_methods_dict["Sig1"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig1"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig1",
                    # "description": f"`{mut_method_name}` and `{method_name}` are the same method"
                    "description": f"`{mut_signature}` and `{method_sig}` are the same method"
                }
            elif paramsReturnType_overlap:
                pattern_methods_dict["Sig2.1"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig2.1"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig2.1",
                    # "description": f"`{mut_method_name}` and `{method_name}` are overloaded methods. They share parameter types `{mut_params_return_type_set & method_params_return_type_set}`."
                    "description": f"`{mut_signature}` and `{method_sig}` are overloaded methods. They share parameter types `{mut_params_return_type_set & method_params_return_type_set}`."
                }
            else:
                pattern_methods_dict["Sig2.2"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig2.2"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig2.2",
                    # "description": f"`{mut_method_name}` and `{method_name}` are overloaded methods. They have different parameter types."
                    "description": f"`{mut_signature}` and `{method_sig}` are overloaded methods. They have different parameter types."
                }
        elif name_token_overlap:
            if paramsReturnType_same:
                pattern_methods_dict["Sig3.1"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig3.1"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig3.1",
                    # "description": f"`{mut_method_name}`'s and `{method_name}`'s names share some name tokens `{set(simple_mut_name_tokens) & set(method_name_tokens)}`. Besides, they have the same parameter type and return type `{mut_params_return_type_set & method_params_return_type_set}`."
                    "description": f"`{mut_signature}`'s and `{method_sig}`'s names share some name tokens `{set(simple_mut_name_tokens) & set(method_name_tokens)}`. Besides, they have the same parameter type and return type `{mut_params_return_type_set & method_params_return_type_set}`."
                }
            elif paramsReturnType_overlap:
                pattern_methods_dict["Sig3.2"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig3.2"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig3.2",
                    # "description": f"`{mut_method_name}`'s and `{method_name}`'s names share some name tokens `{set(simple_mut_name_tokens) & set(method_name_tokens)}`. Besides, they share some parameter types or return type `{mut_params_return_type_set & method_params_return_type_set}`."
                    "description": f"`{mut_signature}`'s and `{method_sig}`'s names share some name tokens `{set(simple_mut_name_tokens) & set(method_name_tokens)}`. Besides, they share some parameter types or return type `{mut_params_return_type_set & method_params_return_type_set}`."
                }
            else:
                pattern_methods_dict["Sig3.3"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig3.3"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig3.3",
                    # "description": f"`{mut_method_name}`'s and `{method_name}`'s names share some name tokens `{set(simple_mut_name_tokens) & set(method_name_tokens)}`. However, they have different parameter types or return type."
                    "description": f"`{mut_signature}`'s and `{method_sig}`'s names share some name tokens `{set(simple_mut_name_tokens) & set(method_name_tokens)}`. However, they have different parameter types or return type."
                }
        else:
            if paramsReturnType_same:
                pattern_methods_dict["Sig4.1"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig4.1"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig4.1",
                    # "description": f"`{mut_method_name}` and `{method_name}` have the same parameter types and return type."
                    "description": f"`{mut_signature}` and `{method_sig}` have the same parameter types and return type."
                }
            elif paramsReturnType_overlap:
                pattern_methods_dict["Sig4.2"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig4.2"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig4.2",
                    # "description": f"`{mut_method_name}` and `{method_name}` share some parameter types or return type `{mut_params_return_type_set & method_params_return_type_set}`."    
                    "description": f"`{mut_signature}` and `{method_sig}` share some parameter types or return type `{mut_params_return_type_set & method_params_return_type_set}`."    
                }
            else:
                pattern_methods_dict["Sig4.3"].append(method_sig)
                pattern_suggested_pairMethods_metadata["Sig4.3"][method_sig] = {
                    "mutA": MUT_signature_w_returnType,
                    "candPairM_sig": method_sig,
                    "pattern_type": "Sig4.3",
                    # "description": f"`{mut_method_name}` and `{method_name}` have different parameter types or return type."
                    "description": f"`{mut_signature}` and `{method_sig}` have different parameter types or return type."
                }
        
        logger.debug("method_sig: %s, method_params_return_type_set: %s, mut_params_return_type_set: %s", 
                    method_sig, method_params_return_type_set, mut_params_return_type_set)
    return pattern_suggested_pairMethods_metadata,pattern_methods_dict



def suggest_paired_methods_by_specific_pattern(MUT_signature_w_returnType: str, pattern: dict, class_under_test_path: str):
    # TODO
    
    pass
    # """
    # Suggest paired methods for the given MUT-A in the class under test.
    
    # ruturn: list of method signatures        
    #     signature example: org.codehaus.gmavenplus.model.LinkTest.testGetters(java.lang.String)
    # """
    # # Get the base method information
    # # change MUT_signature to the base method signature, MUT_signature: org.codehaus.gmavenplus.model.LinkTest.testGetters(java.lang.String) -> base_method: testGetters(String)
    # MUT_signature = MUT_signature_w_returnType
    # base_method_name = MUT_signature.split('(')[0].split('.')[-1]
    # base_method_FQNparams = MUT_signature.split('(')[1].rstrip(')').split(',')
    # base_method_params = [param.split('.')[-1] for param in base_method_FQNparams]
    # base_method = f"{base_method_name}({','.join(base_method_params)})"
    # print(f"base_method: {base_method}", f"base_method_name: {base_method_name}", f"base_method_FQNparams: {base_method_FQNparams}", f"base_method_params: {base_method_params}")
    
    # paired_pattern = pattern["paired_patterns"]
    # print(f"pattern_type: {paired_pattern['pattern_type'] }")
    
    # # Read and parse the class under test file
    # suggested_methods = []
    
    # # Check pattern type and suggest accordingly
    # if paired_pattern["pattern_type"] == 1:
    #     # For identical methods, look for methods with same parameter types
    #     return [MUT_signature]
    
    
    # # try:            
    # # Simple method extraction using basic parsing
    # # This could be enhanced with a proper Java parser like javalang
    # # all_methods_info_str: void:main:String[];void:findFileList:File,List<String>;List<String>:findFileNameListLevel1:String;void:writeTextFile:String,String;String:readTextFile:String;boolean:folderExisting:String;void:folderExistingIfNotCreate:String;boolean:fileExisting:String;String:findPojDir:String,String;String:findPojName:String,String;void:deleteFile:String;void:deleteFilesInFolder:String;void:createFolder:String;
    # print(f"class_under_test_path: {class_under_test_path}")
    # all_methods_info = java_parser.getDeclaredMethodsAndConstructors(class_under_test_path, "getDeclaredMethodsAndConstructors")
    # print(f"all_methods_info: {all_methods_info}")

    
    # for method_info in all_methods_info:
    #     # print(f"method_info: {method_info}") # String:getPackages:void
    #     return_type = method_info.split(':')[0]
    #     name = method_info.split(':')[1]
    #     params = method_info.split(':')[2]
    #     method_sig = f"{name}({params})"
    #     if paired_pattern["pattern_type"] == 2:
    #         # For overloaded methods, look for methods with same name but different parameters
    #         if _is_overloaded_version(method_sig, base_method):
    #             suggested_methods.append(method_sig)
        
    #     else:
    #         # 3: For different method names, check parameter relationships  
    #         if method_sig.split('(')[0] == base_method.split('(')[0]: continue
            
    #         if paired_pattern["pattern_type"] == 3.1:
    #             # Look for methods with same parameter sets
    #             if _has_same_parameters(method_sig, base_method):
    #                 suggested_methods.append(method_sig)
    #         elif paired_pattern["pattern_type"] == 3.2:
    #             # Look for methods with subset/superset parameters
    #             if _has_subset_parameters(method_sig, base_method):
    #                 suggested_methods.append(method_sig)
    #         elif paired_pattern["pattern_type"] == 3.3:
    #             # Look for methods with overlapping parameters
    #             if _has_overlapping_parameters(method_sig, base_method):
    #                 suggested_methods.append(method_sig)
    #         # elif paired_pattern["pattern_type"] == 3.4:
    #         #     # For disjoint parameters, suggest methods with different parameter types
    #         #     # I think, this can be skipped .... 
    #         #     if _has_different_parameters(method_sig, base_method):
    #         #         suggested_methods.append(method_sig)
                        
    # # except Exception as e:
    # #     print(f"Error processing class file: {e}")
    # #     return []
        
    # return suggested_methods
    
    
if __name__ == "__main__":
    suggest_paired_methods_by_specific_pattern("ss", {}, "ss")
    suggest_paired_methods_by_pattern("ss", "ss")