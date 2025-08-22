plugins { /* … */ }

// >>> BEGIN GENERATED (some-block) DO NOT EDIT
// source:
// checksum:
val featureFlag = false
val logLevel by extra("INFO")
param="param value 2"
// <<< END GENERATED

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}
// rest of file...
