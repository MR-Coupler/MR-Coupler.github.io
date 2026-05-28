#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))   # out of date  # This is your Project Root
_PROJECT_NAME = "CyUtil"                         # out of date
SPLITE_STR = "__castle__"


# TO ADD: 
DIR_MAVEN_USER_HOME = ""


# get the path and dir of this file
this_file_dir = os.path.dirname(os.path.abspath(__file__))
cyutil_dir = this_file_dir
bugrevealingmrgen_dir = os.path.dirname(cyutil_dir)
tool_dir = os.path.dirname(bugrevealingmrgen_dir) + "/"
DIR_SOFTWARE = tool_dir + "inputs/env_dependencies/software/"

AUTOMR_JAVA_DEMO_JAR_PATH = f"{DIR_SOFTWARE}demo-1.0-SNAPSHOT-jar-with-dependencies.jar"

# for major
major_home = DIR_SOFTWARE + "major/"
mml_file = DIR_SOFTWARE + "software/major/mml/all.mml.bin"

PATH_MVN = DIR_SOFTWARE + "apache-maven-3.8.5/bin/mvn"
PATH_GRADLE_7_4 = DIR_SOFTWARE + "gradle/gradle-7.4/bin/gradle"
PATH_GRADLE_8_4 = DIR_SOFTWARE + "gradle/gradle-8.4/bin/gradle"
PATH_JAVA = DIR_SOFTWARE + "jdk1.8.0_131/bin/java"

PATH_JAVAC_8 = DIR_SOFTWARE + "zulu_jdks/zulu8.68.0.19-ca-jdk8.0.362-linux_x64/bin/javac" 
PATH_JAVA_8 = DIR_SOFTWARE + "zulu_jdks/zulu8.68.0.19-ca-jdk8.0.362-linux_x64/bin/java"
DIR_JAVA_8 = DIR_SOFTWARE + "zulu_jdks/zulu8.68.0.19-ca-jdk8.0.362-linux_x64/"
PATH_JAVAC_11 = DIR_SOFTWARE + "zulu_jdks/zulu11.62.17-ca-jdk11.0.18-linux_x64/bin/javac" 
PATH_JAVA_11 = DIR_SOFTWARE + "zulu_jdks/zulu11.62.17-ca-jdk11.0.18-linux_x64/bin/java"
DIR_JAVA_11 = DIR_SOFTWARE + "zulu_jdks/zulu11.62.17-ca-jdk11.0.18-linux_x64/"
PATH_JAVAC_13 = DIR_SOFTWARE + "zulu_jdks/zulu13.54.17-ca-jdk13.0.14-linux_x64/bin/javac" 
PATH_JAVA_13 = DIR_SOFTWARE + "zulu_jdks/zulu13.54.17-ca-jdk13.0.14-linux_x64/bin/java"
DIR_JAVA_13 = DIR_SOFTWARE + "zulu_jdks/zulu13.54.17-ca-jdk13.0.14-linux_x64/"
PATH_JAVAC_15 = DIR_SOFTWARE + "zulu_jdks/zulu15.46.17-ca-jdk15.0.10-linux_x64/bin/javac" 
PATH_JAVA_15 = DIR_SOFTWARE + "zulu_jdks/zulu15.46.17-ca-jdk15.0.10-linux_x64/bin/java"
DIR_JAVA_15 = DIR_SOFTWARE + "zulu_jdks/zulu15.46.17-ca-jdk15.0.10-linux_x64/"

PATH_JAVAC_17 = DIR_SOFTWARE + "zulu_jdks/zulu17.40.19-ca-jdk17.0.6-linux_x64/bin/javac" 
PATH_JAVA_17 = DIR_SOFTWARE + "zulu_jdks/zulu17.40.19-ca-jdk17.0.6-linux_x64/bin/java"
DIR_JAVA_17 = DIR_SOFTWARE + "zulu_jdks/zulu17.40.19-ca-jdk17.0.6-linux_x64/"
PATH_JAVAC_18 = DIR_SOFTWARE + "zulu_jdks/zulu18.32.13-ca-jdk18.0.2.1-linux_x64/bin/javac" 
PATH_JAVA_18 = DIR_SOFTWARE + "zulu_jdks/zulu18.32.13-ca-jdk18.0.2.1-linux_x64/bin/java"
DIR_JAVA_18 = DIR_SOFTWARE + "zulu_jdks/zulu18.32.13-ca-jdk18.0.2.1-linux_x64/"
PATH_JAVAC_19 = DIR_SOFTWARE + "zulu_jdks/zulu19.32.13-ca-jdk19.0.2-linux_x64/bin/javac" 
PATH_JAVA_19 = DIR_SOFTWARE + "zulu_jdks/zulu19.32.13-ca-jdk19.0.2-linux_x64/bin/java"
DIR_JAVA_19 = DIR_SOFTWARE + "zulu_jdks/zulu19.32.13-ca-jdk19.0.2-linux_x64/"
PATH_JAVAC_21 = DIR_SOFTWARE + "zulu_jdks/zulu21.32.17-ca-jdk21.0.2-linux_x64/bin/javac" 
PATH_JAVA_21 = DIR_SOFTWARE + "zulu_jdks/zulu21.32.17-ca-jdk21.0.2-linux_x64/bin/java"
DIR_JAVA_21 = DIR_SOFTWARE + "zulu_jdks/zulu21.32.17-ca-jdk21.0.2-linux_x64/"

MVN_PATH = f"{DIR_SOFTWARE}/apache-maven-3.8.5/bin/mvn"
RANDOOP431_JAR_PATH = DIR_SOFTWARE + "randoop/randoop-4.3.1/randoop-all-4.3.1.jar"
# PATH_EVOSUITE_JAR = DIR_SOFTWARE + "evosuite/evosuite-1.2.0.jar"
PATH_EVOSUITE_JAR = DIR_SOFTWARE + "evosuite/evosuite-master-1.2.1-SNAPSHOT.jar" # updated by hc
PATH_ES_RUNTIME_JAR = DIR_SOFTWARE + "evosuite/evosuite-standalone-runtime-1.2.0.jar"
PATH_JUNIT4_JAR =DIR_SOFTWARE + "junit/junit-4.13.2.jar"
PATH_JUNIT5_JAR =DIR_SOFTWARE + "junit/junit-jupiter-api-5.8.2.jar"
PATH_OPENTT4J_JAR = DIR_SOFTWARE + "junit/opentest4j-1.2.0.jar"
PATH_JUNIT5_STANDALONE_JAR =DIR_SOFTWARE + "junit/junit-platform-console-standalone-1.10.0.jar"
PATH_HAMCREST_CORE_JAR =DIR_SOFTWARE + "junit/hamcrest-core-1.3.jar"
PATH_PITEST_JAR =DIR_SOFTWARE + "pitest/pitest-1.8.0.jar"
PATH_PITEST_CMD_JAR =DIR_SOFTWARE + "pitest/pitest-command-line-1.8.0.jar"
PATH_PITEST_ENTRY_JAR =DIR_SOFTWARE + "pitest/pitest-entry-1.8.0.jar"
PATH_PITEST_JUNIT5_PLUGIN_JAR =DIR_SOFTWARE + "pitest/pitest-junit5-plugin-0.16.jar"

ASSERTION_FAILURE_LIST = ["java.lang.AssertionError", "org.junit.ComparisonFailure", "org.junit.internal.AssertionError", "org.testng.AssertionError", "junit.framework.AssertionFailedError" , "org.opentest4j.AssertionFailedError"]