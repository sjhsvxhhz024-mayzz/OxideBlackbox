package top.niunaijun.blackbox.core.system.api;

public class MetaActivationManager {

    private static boolean licenseActivated = false;
    private static String licenseMessage = "";
    
    public static void activateSdk(String licenseKey) {
        LicenseVerifier.verify(licenseKey, new LicenseVerifier.Callback() {
			@Override
			public void onResult(boolean isValid, String message) {
				licenseActivated = isValid;
				licenseMessage = message;
			}
		});
    }

    public static boolean isLicenseActivated() {
        return licenseActivated;
    }
}
