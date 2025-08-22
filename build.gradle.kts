plugins { /* … */ }

// >>> BEGIN GENERATED (first-block) DO NOT EDIT
// source:
// checksum:
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
