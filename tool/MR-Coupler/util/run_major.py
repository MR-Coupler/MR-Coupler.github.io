import os
import subprocess
import logging
from typing import Union, List

from util import java_file_processing, java_test

major_home = "TO_CONFIG"
mml_file = "TO_CONFIG"

def run_major(
    poj_dir: str,
    source_files: Union[str, List[str]], 
    output_dir: str,
    classpath: str = "",
    additional_args: List[str] = None,
    java_home: str = None,
    poj_build_tool: str = "maven"
    
) -> bool:
    """
    Run the Major mutation testing tool on specified source files.
    
    Args:
        major_home: Path to Major installation directory
        source_files: Java source file(s) to mutate (string or list of strings)
        output_dir: Directory where mutant class files will be stored
        classpath: Java classpath to use (passed with -cp)
        mml_file: Path to the MML file (defaults to $MAJOR_HOME/mml/all.mml.bin)
        additional_args: Additional arguments to pass to Major
        java_home: Optional JAVA_HOME to use (will set in environment if provided)
        
    Returns:
        True if Major ran successfully, False otherwise
    """
    global major_home, mml_file
    
    # Normalize paths
    major_home = os.path.expanduser(major_home)
    
    # Validate Major installation
    major_bin = os.path.join(major_home, "bin", "major")
    if not os.path.isfile(major_bin):
        logging.error(f"Major executable not found at: {major_bin}")
        return False
    
    # Set default MML file if not provided
    if mml_file is None:
        mml_file = os.path.join(major_home, "mml", "all.mml.bin")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare source files argument
    if isinstance(source_files, str):
        source_files = [source_files]
    
    # Build command
    cmd = [
        major_bin,
        "--mml", mml_file
    ]
    
    # Add classpath 
    class_dir_list, jar_dir_list = java_file_processing.get_all_target_classes_and_jars_relative_path(dir=poj_dir, include_test_classes=True, poj_build_tool=poj_build_tool)
    all_class_dir_str = (":").join( class_dir_list )
    all_jar_list_str = (":").join( jar_dir_list )
    Dir_ClassPath = f".:{java_test.JUNIT_JARS_CP_str}:{all_class_dir_str}:{all_jar_list_str}"
    CP_content = f"{Dir_ClassPath}:{classpath}"
    
    cmd.extend(["-cp", CP_content])
    
    # Add output directory
    cmd.extend(["-d", output_dir])
    
    # Add any additional arguments
    if additional_args:
        cmd.extend(additional_args)
    
    # Add source files
    cmd.extend(source_files)
    
    cmd_w_java_home = f'JAVA_HOME="{java_home}"; PATH="$JAVA_HOME/bin:$PATH"; cd {poj_dir}; {" ".join(cmd)}'
    # Log the command
    logging.info(f"run_major: Running Major with command: {' '.join(cmd)}")
    print(f"run_major: Running Major with command: {' '.join(cmd)}")
    
    # Set up environment
    env = os.environ.copy()
    if java_home:
        env["JAVA_HOME"] = java_home
        env["PATH"] = f"{os.path.join(java_home, 'bin')}:{env.get('PATH', '')}"
        logging.info(f"run_major: Using JAVA_HOME: {java_home}")
        print(f"run_major: Using JAVA_HOME: {java_home}")
    try:
        # Run the command
        result = subprocess.run(
            cmd, 
            check=True,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=poj_dir
        )
        print(f"run_major: cmd_result: {result.returncode}")
        
        
        class_name = source_files[0].split("/")[-1].split(".")[0]
        for file in os.listdir(poj_dir):
            if file == "major.log":
                os.rename(os.path.join(poj_dir, file), os.path.join(output_dir, file.replace("major.log", f"{class_name}.major.log")))
            elif file == "mutants.log":
                os.rename(os.path.join(poj_dir, file), os.path.join(output_dir, file.replace("mutants.log", f"{class_name}.mutants.log")))
            elif file == "suppression.log":
                os.rename(os.path.join(poj_dir, file), os.path.join(output_dir, file.replace("suppression.log", f"{class_name}.suppression.log")))
        
        logging.info(f"Major completed successfully")
        logging.debug(f"Output: {result.stdout}")
        if result.returncode == 0:
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Major failed with exit code {e.returncode}")
        logging.error(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Failed to run Major: {str(e)}")
        return False
    
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    test_run_major() 