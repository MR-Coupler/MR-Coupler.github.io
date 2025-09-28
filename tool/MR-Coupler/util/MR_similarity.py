"""
Measuring the similarity of encoded MR based on the MR skeleton (Setup-Execute-Verify)
Input relations: Input transformation (if available) 
(1) Same API / operations?      	-> intersection/overlap
(2) Same involved input set?   	-> intersection/overlap
symbolic: $Type sourceInput1, …. $Type sourceOutput1, $Type sourceOutput2 … $Type followUpInput1, … 
Execution: MR involved method invocations
(3) sequence of involved methods 	 -> intersection/overlap
List of involved method signatures -> 1- edit distance? 
(The parameter/returnType relations are already included in the List of involved method signatures)
Verify: output relation
(4) assertiontype				-> intersection/overlap
assertion API
(5) assertion involved elements  	  	-> intersection/overlap
symbolic: $Type sourceInput1, …. $Type sourceOutput1, $Type sourceOutput2 … $Type followUpInput1, … 

the same skeleton:  -> similar encode MRs
used input transformation function/operations (1)
sequence of MR-involved methods (3)-set/list
relation assertion function (4) + involved elements
e.g.,assertEquals, assertNotEquals, …. 

level1: the same MR-involved methods – set
level2: ~ 
+ input transformation functions (if any )
+ relation assertion function (4) + involved elements

+ similar bug-detection capability



------
implement:
* method invocation (use the method name or signature)?
* input transformation: if developer-written MR does not have input transformation, just directly take as the same
"""

import os
from util import file_processing,json_processing, java_parser, compile_java_poj, java_test, config, java_file_processing, PIT
import re

class MRMetaInfo:
    def __init__(self):
        self.with_input_transformation = None
        self.method_invocations = None
        self.relation_assertion_api = None
        self.relation_assertion_stmt = None
        self.relation_assertion_elements = None
        self.MRScout_result_path = None
    
    @staticmethod
    def extract_MR_meta_info(MRScout_result_path, MR_object=None):
        print("extract_MR_meta_info, MRScout_result_path: ", MRScout_result_path)
        # example: /data/projects_bugAfix/org.dyn4j.world.AbstractCollisionWorldTest.convexCast/latest/org.dyn4j.world.AbstractCollisionWorldTest_convexCast_P4_2.testMR__example__0.json
        if MR_object is None: MR_object = MRMetaInfo()
        MR_object.MRScout_result_path = MRScout_result_path
        MRScout_result = json_processing.read(MRScout_result_path)
    
        # self.with_input_transformation
        MR_object.with_input_transformation = MRScout_result["withInputTransformation_Option1"]
        # self.method_invocations
        lastMethodInvocation = MRScout_result["lastMethodInvocation"]
        previousMethodInvocations = []
        for i in range(len(MRScout_result["previousMethodInvocations"])):
            if "mceQualifiedSignature" in MRScout_result["previousMethodInvocations"][i]:
                previousMethodInvocations.append(MRScout_result["previousMethodInvocations"][i])
        MR_object.method_invocations = [lastMethodInvocation["mceQualifiedSignature"]] + [invocation["mceQualifiedSignature"] for invocation in previousMethodInvocations]
        MR_object.method_invocations = [ ele.split("(")[0] for ele in MR_object.method_invocations]
        MR_object.method_invocations = [ ele.split("(")[0].split(".")[-1] for ele in MR_object.method_invocations]
            
        
        # self.relation_assertion_stmt
        assertionSTMT = MRScout_result["assertionSTMT"]
        MR_object.relation_assertion_stmt = assertionSTMT
        # self.relation_assertion_api
        relation_assertion_api = assertionSTMT.split("(")[0].split(".")[-1]
        MR_object.relation_assertion_api = relation_assertion_api
        
        # self.relation_assertion_elements 
        relation_assertion_elements = []
        for invocation in [lastMethodInvocation] : # follow-up output
            outputExpressions = invocation["outputExpressions"]
            # mceQualifiedSignature = invocation["mceQualifiedSignature"]
            for i in range(len(outputExpressions)):
                if outputExpressions[i] in assertionSTMT:
                    relation_assertion_elements.append(f"FollowUpOutput_{i}")
        for invocation_i in range(len(previousMethodInvocations)): # source output
            invocation = previousMethodInvocations[invocation_i]
            outputExpressions = invocation["outputExpressions"]
            for i in range(len(outputExpressions)):
                if outputExpressions[i] in assertionSTMT:
                    relation_assertion_elements.append(f"SourceOutput{invocation_i}_{i}")
        MR_object.relation_assertion_elements = relation_assertion_elements
        
        return MR_object

def assertType_normalization(assertionSTMT):
    """
    principle: no FP
    
    # boolAssert -> compAssert
    assertTrue( x.equal(y) ) -> assertEqual(x,y)
    assertFalse( x.equal(y) ) -> assertNotEqual(x,y)
    
    assertTrue( x == y ) -> assertSame(x,y)
    assertFalse( x == y ) -> assertNotSame(x,y)
    assertTrue(x != y) -> assertNotSame(x,y)
    assertFalse(x != y) -> assertSame(x,y)
    
    assertTrue(list.contains(x)) -> assertIn(x, list)
    assertFalse(list.contains(x)) -> assertNotIn(x, list)
    
    
    assertTrue(x > y) -> assertGreaterThan(x, y) *
    assertTrue(x >= y) ->  assertGreaterThanOrEqual(x, y) *
    assertTrue(x < y) ->  assertLessThan(x, y) *
    assertTrue(x <= y)  ->  assertLessThanOrEqual(x, y) *

    assertThat(x, is(y)) -> assertEquals(y, x)
    assertThat(x, not(y)) -> assertNotEquals(y, x)

    ... 
    """

    relation_assertion_api = assertionSTMT.split("(")[0].split(".")[-1]
    stmt = assertionSTMT
    
    # Patterns for normalization
    if relation_assertion_api == "assertTrue" and re.search(r"\.equals\(", stmt):
        return "assertEqual"
    if relation_assertion_api == "assertFalse" and re.search(r"\.equals\(", stmt):
        return "assertNotEqual"
    if relation_assertion_api == "assertTrue":
        if re.search(r"\s*==\s*", stmt):
            return "assertSame"
        if re.search(r"!=", stmt):
            return "assertNotSame"
        if re.search(r">=", stmt):
            return "assertGreaterThanOrEqual"
        if re.search(r">", stmt):
            return "assertGreaterThan"
        if re.search(r"<=", stmt):
            return "assertLessThanOrEqual"
        if re.search(r"<", stmt):
            return "assertLessThan"
        if re.search(r"\.contains\(", stmt):
            return "assertIn"
    if relation_assertion_api == "assertFalse":
        if re.search(r"\s*==\s*", stmt):
            return "assertNotSame"
        if re.search(r"!=", stmt):
            return "assertSame"
        if re.search(r"\.contains\(", stmt):
            return "assertNotIn"
    if relation_assertion_api == "assertThat":
        if re.search(r",\s*is\s*\(", stmt):
            return "assertEquals"
        if re.search(r",\s*not\s*\(", stmt):
            return "assertNotEquals"
    if relation_assertion_api in ["assertEquals", "assertEqual"]:
        return "assertEqual"
    if relation_assertion_api in ["assertNotEquals", "assertNotEqual"]:
        return "assertNotEqual"
    return relation_assertion_api
  
        
def get_developer_written_MTC_metainfo(MR_generator):
    MTC_item = MR_generator.MTC_item
    poj_dir = MTC_item["poj_dir"]
    FQS_MTC = MTC_item["FQS"]
    FQN_MTC = FQS_MTC.replace("()", "")
    
    MRs_meta_info = []
    MRScout_result_dir = f"{poj_dir}/AutoMR/MTidentifier/"
    for filename in file_processing.walk_L1_FileNames(MRScout_result_dir):
        if filename.startswith(FQN_MTC) and filename.endswith('.json') and config.SPLITE_STR in filename:
            path_of_MRScout_result = f"{MRScout_result_dir}/{filename}"
            MR_meta_info = MRMetaInfo.extract_MR_meta_info(path_of_MRScout_result)
            MRs_meta_info.append(MR_meta_info)
    
    return MRs_meta_info
    
    

def get_generatedMR_metainfo(MR_generator):
    poj_dir = MR_generator.MTC_version_poj_dir
    genreated_test_class_FQN = MR_generator.genreated_test_class_FQN
    paths_of_MRScout_result = []
    
    MRs_meta_info = []
    MRScout_result_dir = f"{poj_dir}"
    for filename in file_processing.walk_L1_FileNames(poj_dir):
        if filename.startswith(genreated_test_class_FQN) and filename.endswith('.json') and config.SPLITE_STR in filename:
            path_of_MRScout_result = f"{MRScout_result_dir}/{filename}"
            MR_meta_info = MRMetaInfo.extract_MR_meta_info(path_of_MRScout_result)
            MRs_meta_info.append(MR_meta_info)
    return MRs_meta_info


def compare_similiarity_based_on_skeleton(generatedMRs_meta_info, developerMRs_meta_info):
    similiarity_based_on_skeleton = {
        "same_method_invocations": {},
        "same_input_transformation": {},
        "same_relation_assertion_api": {},
        "same_relation_assertion_elements": {}
    }
    
    for generatedMR_meta_info in generatedMRs_meta_info:
        for developerMR_meta_info in developerMRs_meta_info:
            # same method invocations (set)
            if set(generatedMR_meta_info.method_invocations) == set(developerMR_meta_info.method_invocations):
                similiarity_based_on_skeleton["same_method_invocations"][generatedMR_meta_info.MRScout_result_path] = developerMR_meta_info.MRScout_result_path
            elif set(generatedMR_meta_info.method_invocations).issuperset( set(developerMR_meta_info.method_invocations) ):
                similiarity_based_on_skeleton["same_method_invocations"][generatedMR_meta_info.MRScout_result_path] = developerMR_meta_info.MRScout_result_path
            
            # same input transformation
            if developerMR_meta_info.with_input_transformation == True: 
                if generatedMR_meta_info.with_input_transformation == developerMR_meta_info.with_input_transformation:
                    similiarity_based_on_skeleton["same_input_transformation"][generatedMR_meta_info.MRScout_result_path] = developerMR_meta_info.MRScout_result_path
            else:
                similiarity_based_on_skeleton["same_input_transformation"][generatedMR_meta_info.MRScout_result_path] = developerMR_meta_info.MRScout_result_path
            
            # same relation assertion api
            if generatedMR_meta_info.relation_assertion_api == developerMR_meta_info.relation_assertion_api:
                similiarity_based_on_skeleton["same_relation_assertion_api"][generatedMR_meta_info.MRScout_result_path] = developerMR_meta_info.MRScout_result_path
            
            # same relation assertion elements
            if set(generatedMR_meta_info.relation_assertion_elements) == set(developerMR_meta_info.relation_assertion_elements):
                similiarity_based_on_skeleton["same_relation_assertion_elements"][generatedMR_meta_info.MRScout_result_path] = developerMR_meta_info.MRScout_result_path
    
    return similiarity_based_on_skeleton

def measure_similarity_of_generatedMR_and_developer_written_MTC(MR_generator):
    result = {
        "level1-same_method_invocations": None,
        "level2-same_skeleton": None
    }
    generatedMRs_meta_info = get_generatedMR_metainfo(MR_generator)
    developerMRs_meta_info = get_developer_written_MTC_metainfo(MR_generator)
    
    similiarity_based_on_skeleton = compare_similiarity_based_on_skeleton(generatedMRs_meta_info, developerMRs_meta_info)
    if len(similiarity_based_on_skeleton["same_method_invocations"]) > 0:
        result["level1-same_method_invocations"] = similiarity_based_on_skeleton["same_method_invocations"]
        
        if len(similiarity_based_on_skeleton["same_relation_assertion_api"]) > 0:
            if len(similiarity_based_on_skeleton["same_relation_assertion_elements"]) > 0:
                if len(similiarity_based_on_skeleton["same_input_transformation"]) > 0:
                    result["level2-same_skeleton"] = similiarity_based_on_skeleton["same_relation_assertion_elements"]
    return result
 
 
 
def test_assertType_normalization():
    """
    principle: no FP
    
    # boolAssert -> compAssert
    assertTrue( x.equal(y) ) -> assertEqual(x,y)
    """ 
    assertionSTMT = "assertTrue( x.equals(y) ) "
    result = assertType_normalization(assertionSTMT)
    assert result == "assertEqual", f"Expected 'assertEqual', but got {result}"

def test_():
    generated_path = "/data/BugRev/projects_bugAfix/com.alipay.sofa.rpc.config.RegistryConfigTest.testAll/latest/com.alipay.sofa.rpc.config.RegistryConfigTest_testAll_P1_0.testMR__example__0.json"
    generated_meta_info = MRMetaInfo.extract_MR_meta_info(generated_path)
    GT_path = "/data/BugRev/projects_MTidentifier_relationAssertion_outputs/example__create-react-app-project/com.alipay.sofa.rpc.config.RegistryConfigTest.testAll__example__0.json"
    GT_meta_info = MRMetaInfo.extract_MR_meta_info(GT_path)

    result = {
        "level1-same_method_invocations": None,
        "level2-same_skeleton": None
    }
    similiarity_based_on_skeleton = compare_similiarity_based_on_skeleton([generated_meta_info], [GT_meta_info])
    
    if len(similiarity_based_on_skeleton["same_method_invocations"]) > 0:
        result["level1-same_method_invocations"] = similiarity_based_on_skeleton["same_method_invocations"]
        
        if len(similiarity_based_on_skeleton["same_relation_assertion_api"]) > 0:
            if len(similiarity_based_on_skeleton["same_relation_assertion_elements"]) > 0:
                if len(similiarity_based_on_skeleton["same_input_transformation"]) > 0:
                    result["level2-same_skeleton"] = similiarity_based_on_skeleton["same_relation_assertion_elements"]
    print("test_ result: ", result)


def all_tests():
    test_assertType_normalization()
    test_() 

if __name__ == "__main__":
    all_tests()