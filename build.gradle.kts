plugins { /* … */ }

// >>> BEGIN GENERATED (first-block) DO NOT EDIT
// source:
// checksum:
val featureFlag = false
val logLevel by extra("INFO")
param="param value 1"
// <<< END GENERATED

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

// using gh variables
val someVar = {{ vars.VAR1 }}
val someVar2 = {{ vars.VAR2 }}

// rest of file...
