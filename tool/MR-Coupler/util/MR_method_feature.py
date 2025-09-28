"""
    Feature based on signatures of methods m1 and m2  
    

    ---------
    features from categories of paired methods
        (method invocaiton)
        * [Composition operation] 
            m1 is invoked in m2
        * [Specialization] 
            m1 is conditionally invoked in m2
        * [overlapping dependency]
            overlapping dependency (invoked API/fields)

        (state update/access)
        * [Producer-consumer] 
            Some fields are ( indirectly ) updated by m1 ->  accessed by m2
        * [overlapping production] 
            overlapping outputs (updated fields/outputs)

        * [Inverse] == included in the pattern
            same/inverse data type conversion
        * [Equivalence relation]  == included in the pattern
            same method name (overloading)?


    features from FN/FP 
        * shared accessed fields ..
        * the `repos()` is a part of `randomReop()`, invoked inside `randomReop()`

    
    "MI":
      1. muta invoked in mutb
      2. mutb invoked in muta
      3. muta and mutb share the same invoked methods
    
    "State" state
        1. muta updates fields, mutb accesses the updated fields
        2. mutb updates fields, muta accesses the updated fields
        3. muta and mutb share the same accessed fields
        4. muta and mutb share the same updated fields


"""

import re
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from util import java_parser, java_file_processing, json_processing
from bugrevealingmrgen.util.MR_method_pattern import parse_method_signature


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


def get_method_invocation_withinMethod(java_class_path, target_method):
    """
        input: 
            * java_class_path:
            * target_method: # in the form of String:getPackages:void

        output:
            ["serializeMeta()","serializeMeta()","contains(Unresolved)"]
    """
    method_invocations = java_parser.getInvokedMethodsInaMethod(java_class_path, target_method,function="getInvokedMethodsInaMethod")
    return method_invocations

def get_accessORupdate_field_withinMethod(java_class_path, target_method):
    """
        input: 
            * java_class_path:
            * target_method: # in the form of String:getPackages:void
        
        output:
            * result: {
            "accessedFields":["INCLUDE_META"],"updatedFields":[]}
    """
    result = java_parser.getAccessORUpdatedFiledsInaMethod(java_class_path, target_method,function="getAccessORUpdatedFiledsInaMethod")
    return result


def suggest_paired_methods_by_feature(MUT_signature_w_returnType: str, class_under_test_path: str):
    """
    Suggest paired methods for the given MUT-A in the class under test.
    
    "MI":
      1. muta invoked in mutb
      2. mutb invoked in muta
      3. muta and mutb share the same invoked methods
    
    "S" state
        1. muta updates fields, mutb accesses the updated fields
        2. mutb updates fields, muta accesses the updated fields
        3. muta and mutb share the same accessed fields
        4. muta and mutb share the same updated fields
        
    """
    # Get the base method information
    mut_method_name, simple_mut_name_tokens, mut_simple_params, mut_return_type = parse_method_signature(MUT_signature_w_returnType)
    simple_mut_method_name = mut_method_name.split('.')[-1]
    mut_method_name = simple_mut_method_name
    mut_params  = mut_simple_params
    mut_signature = f"{mut_method_name}({','.join(mut_params)})"
    mut_signature = mut_signature.replace("(void)", "()") # special operation-void
    # mut_params.replace("void","NA")  # Remove 'void' from parameters if present


    logger.debug("class_under_test_path: %s", class_under_test_path)
    all_methods_info = java_parser.getDeclaredMethodsAndConstructors(class_under_test_path, "getDeclaredMethodsAndConstructors")
    logger.debug("all_methods_info: %s", all_methods_info)

    
    formatted_MUT = f"{mut_return_type}:{mut_method_name}:{','.join(mut_params)}"
    muta_name = mut_method_name
    muta_simple_name = mut_method_name.split('.')[-1]
    muta_method_invocations = get_method_invocation_withinMethod(class_under_test_path, formatted_MUT)
    muta_method_invocation_just_name = [inv.split("(")[0].split(".")[-1] for inv in muta_method_invocations] if muta_method_invocations and len(muta_method_invocations) > 0 else []
    muta_accessedORupdated_fields = get_accessORupdate_field_withinMethod(class_under_test_path, formatted_MUT)
    if muta_accessedORupdated_fields == None: # just use the default value
        muta_accessedORupdated_fields = {"accessedFields": [], "updatedFields": []}
    feature_methods_dict_metadata = { "MI1": {}, "MI2": {}, "MI3": {}, "State1": {}, "State2": {}, "State3": {}, "State4": {} }
    feature_methods_dict = { "MI1": [], "MI2": [], "MI3": [], "State1": [], "State2": [], "State3": [], "State4": [] }
    for formatted_method_info in all_methods_info:
        # formatted_method_info: String:getPackages:void
        candPairM_method_return_type = formatted_method_info.split(':')[0]
        candPairM_method_name = formatted_method_info.split(':')[1]
        candPairM_method_params = formatted_method_info.split(':')[2]

        if candPairM_method_name == "extract": # jus for debug
            pass
        candPairM_name  = candPairM_method_name
        candPairM_simple_name = candPairM_name.split('.')[-1]

        candPairM_sig = f"{candPairM_method_name}({candPairM_method_params})"
        candPairM_sig = candPairM_sig.replace("(void)","()")  # Remove 'void' from parameters if present    
        candPairM_method_invocations =  get_method_invocation_withinMethod(class_under_test_path, formatted_method_info)
        candPairM_method_invocation_just_name = [inv.split("(")[0].split(".")[-1] for inv in candPairM_method_invocations] if candPairM_method_invocations and len(candPairM_method_invocations) > 0 else []
        candPairM_accessedORupdated_fields = get_accessORupdate_field_withinMethod(class_under_test_path, formatted_method_info)
        if candPairM_accessedORupdated_fields == None: # just use the default value
            candPairM_accessedORupdated_fields = {"accessedFields": [], "updatedFields": []}

        if candPairM_simple_name in muta_method_invocation_just_name:
            # 1. muta invoked in mutb
            if candPairM_sig in feature_methods_dict["MI1"]: continue # avoid duplicate entries
            feature_methods_dict_metadata["MI1"][candPairM_sig] = {
                "mutA": formatted_MUT,
                "candPairM": formatted_method_info,
                "candPairM_sig": candPairM_sig,
                "feature": "MI1",
                # "description": f"`{candPairM_simple_name}` is invoked in `{muta_simple_name}`"
                "description": f"`{mut_signature}` invokes `{candPairM_sig}`"
            }
            feature_methods_dict["MI1"].append(candPairM_sig)
        if muta_simple_name in candPairM_method_invocation_just_name:
            # 2. mutb invoked in muta
            if candPairM_sig in feature_methods_dict["MI2"]: continue # avoid duplicate entries
            feature_methods_dict_metadata["MI2"][candPairM_sig] = {
                "mutA": formatted_MUT,
                "candPairM": formatted_method_info,
                "candPairM_sig": candPairM_sig,
                "feature": "MI2",
                # "description": f"`{muta_simple_name}` is invoked in `{candPairM_simple_name}`"
                "description": f"`{mut_signature}` is invoked in `{candPairM_sig}`"
            }
            feature_methods_dict["MI2"].append(candPairM_sig)
        if set(muta_method_invocation_just_name) & set(candPairM_method_invocation_just_name):
            # 3. muta and mutb share the same invoked methods
            shared_method_invocations = set(muta_method_invocation_just_name) & set(candPairM_method_invocation_just_name)
            if candPairM_sig in feature_methods_dict["MI3"]: continue # avoid duplicate entries
            feature_methods_dict_metadata["MI3"][candPairM_sig] = {
                "mutA": formatted_MUT,
                "candPairM": formatted_method_info,
                "candPairM_sig": candPairM_sig,
                "feature": "MI3",
                "shared_method_invocations": list(shared_method_invocations),
                # "description": f"`{muta_simple_name}` and `{candPairM_simple_name}` share the same invoked methods `{shared_method_invocations}`"
                "description": f"`{mut_signature}` and `{candPairM_sig}` share the same invoked methods `{shared_method_invocations}`"
            }
            feature_methods_dict["MI3"].append(candPairM_sig)
        
        for muta_access in muta_accessedORupdated_fields["accessedFields"]:
            if muta_access in candPairM_accessedORupdated_fields["updatedFields"]:
                # 1. muta updates fields, mutb accesses the updated fields
                if candPairM_sig in feature_methods_dict["State1"]: continue # avoid duplicate entries
                feature_methods_dict_metadata["State1"][candPairM_sig] = {
                    "mutA": formatted_MUT,
                    "candPairM": formatted_method_info,
                    "candPairM_sig": candPairM_sig,
                    "feature": "State1",
                    # "description": f"`{muta_name}` updates `{muta_access}`, `{candPairM_name}` accesses the updated field `{muta_access}`"
                    "description": f"`{mut_signature}` updates `{muta_access}`, `{candPairM_sig}` accesses the updated field `{muta_access}`"
                }
                feature_methods_dict["State1"].append(candPairM_sig)
            if muta_access in candPairM_accessedORupdated_fields["accessedFields"]:
                # 2. mutb updates fields, muta accesses the updated fields
                if candPairM_sig in feature_methods_dict["State2"]: continue # avoid duplicate entries
                feature_methods_dict_metadata["State2"][candPairM_sig] = {
                    "mutA": formatted_MUT,
                    "candPairM": formatted_method_info,
                    "candPairM_sig": candPairM_sig,
                    "feature": "State2",
                    # "description": f"`{candPairM_name}` updates `{muta_access}`, `{muta_name}` accesses the updated field `{muta_access}`"
                    "description": f"`{candPairM_sig}` updates `{muta_access}`, `{mut_signature}` accesses the updated field `{muta_access}`"
                }
                feature_methods_dict["State2"].append(candPairM_sig)
        if set(muta_accessedORupdated_fields["accessedFields"]) & set(candPairM_accessedORupdated_fields["accessedFields"]):
            # 3. muta and mutb share the same accessed fields
            shared_accessed_fields = set(muta_accessedORupdated_fields["accessedFields"]) & set(candPairM_accessedORupdated_fields["accessedFields"])
            if candPairM_sig in feature_methods_dict["State3"]: continue # avoid duplicate entries
            feature_methods_dict_metadata["State3"][candPairM_sig] = {
                "mutA": formatted_MUT,
                "candPairM": formatted_method_info,
                "candPairM_sig": candPairM_sig,
                "feature": "State3",
                "shared_accessed_fields": list(shared_accessed_fields),
                # "description": f"`{muta_name}` and `{candPairM_name}` share the same accessed fields `{shared_accessed_fields}`"
                "description": f"`{mut_signature}` and `{candPairM_sig}` share the same accessed fields `{shared_accessed_fields}`"
            }
            feature_methods_dict["State3"].append(candPairM_sig)
        if set(muta_accessedORupdated_fields["updatedFields"]) & set(candPairM_accessedORupdated_fields["updatedFields"]):
            # 4. muta and mutb share the same updated fields
            shared_updated_fields = set(muta_accessedORupdated_fields["updatedFields"]) & set(candPairM_accessedORupdated_fields["updatedFields"])
            if candPairM_sig in feature_methods_dict["State4"]: continue # avoid duplicate entries
            feature_methods_dict_metadata["State4"][candPairM_sig] = {
                "mutA": formatted_MUT,
                "candPairM": formatted_method_info,
                "candPairM_sig": candPairM_sig,
                "feature": "State4",
                "shared_updated_fields": list(shared_updated_fields),
                # "description": f"`{muta_name}` and `{candPairM_name}` share the same updated fields `{shared_updated_fields}`"
                "description": f"`{mut_signature}` and `{candPairM_sig}` share the same updated fields `{shared_updated_fields}`"
            }
            feature_methods_dict["State4"].append(candPairM_sig)

    return feature_methods_dict_metadata, feature_methods_dict


def test_suggest_paired_methods_by_feature():
    all_MTCs = json_processing.read('/data/MTidentifier_result_example.json')
    
    test_cases = {
        "io.opentracing.mock.MockTracerTest.testTextMapPropagatorTextMap()": "State", # shared class field
        "org.eclipse.angus.mail.util.logging.CompactFormatterTest.testFormatBackTraceEvilIgnore()":"MI2", # inside invocation
        "com.jcabi.github.mock.MkGithubTest.canCreateRandomRepo()": "MI", # inside invocation
        "com.fasterxml.jackson.core.jsonptr.JsonPointerTest.equality()": "State", # shared class field
    }
    for MR_item in all_MTCs["MR_items"]:
        if len(MR_item) == 0: continue
        
        FQS_testMethods = MR_item["FQS_testMethos"]
        if FQS_testMethods not in test_cases.keys(): continue        
        print("testing", FQS_testMethods)
                     
        poj_name = MR_item["poj_name"]
        test_file_path = MR_item["test_file_path"]        
        target_methods_FQS = MR_item["invoked_methods_FQS"][0]
        GT = MR_item["invoked_methods_FQS"][-1]
        simplified_GT = MR_item["invoked_methods_FQS"][-1].split('(')[0].split('.')[-1]
        MUTa_signature = target_methods_FQS

        # special: 
        if "JsonPointerTest" in FQS_testMethods: simplified_GT = "empty"
        
        
        poj_dir = test_file_path.split(poj_name)[0] + poj_name
        class_path, MUT_code, return_type = java_file_processing.get_classPath_methodCode_returnType(MUTa_signature, poj_dir)
        MUTa_signature_w_returnType = f"{return_type} {MUTa_signature}"
        class_under_test_path = class_path
        
        # method execution
        feature_methods_dict_metadata, feature_methods_dict = suggest_paired_methods_by_feature(MUTa_signature_w_returnType, class_under_test_path)
        
        assert_flag = False
        for feature_name in feature_methods_dict.keys():
            if not feature_name.startswith(test_cases[FQS_testMethods]):continue
            if len(feature_methods_dict[feature_name]) == 0: continue
            if simplified_GT in [ method.split("(")[0] for method in feature_methods_dict[feature_name]]:
                assert_flag = True
                break
            
        if not assert_flag:
            print("GT:", GT, "simplified_GT:", simplified_GT)
            print("feature_methods_dict_metadata:", feature_methods_dict_metadata)
            print("feature_methods_dict:", feature_methods_dict)
            print("------------")
        print("ASSERT_RESULT: ", assert_flag)
        print("--------------------------------")


if __name__ == "__main__":
    # suggest_paired_methods_by_feature("ss", "ss")
    test_suggest_paired_methods_by_feature()