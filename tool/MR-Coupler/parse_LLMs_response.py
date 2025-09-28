from util import file_processing,json_processing



def extract_generated_class(response_content, generated_class_name):
    code_lines = []
    code_flag = False
    codes = []
    code=[]
    for line in response_content.split("\n"):
      if code_flag==False and line.strip().startswith("```"):
        code_flag = True
        continue
      if code_flag==True and line.strip().startswith("```"):
         code_flag = False
         code = ("\n").join(code_lines)
         codes.append(code)
         code=[]
         code_lines = []
      if code_flag:
        code_lines.append(line)
    

    class_code = ""
    for code in codes:
       if f"class {generated_class_name}" in code:
          class_code = code
          break
    
    return code

