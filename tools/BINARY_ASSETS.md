# Binary assets (base64)

All binary files in this project are committed as `*.b64` (base64 text) because the
import channel could not carry raw binary git blobs. Restore them before building:

```
bash tools/restore_binaries.sh
```

This regenerates the real PNGs, JARs, the native `Bcore/src/main/res/raw/temp`,
and `gradle/wrapper/gradle-wrapper.jar`. After that the project builds normally
(`./gradlew :app:assembleDebug`).
