package top.niunaijun.blackbox.fake.service;

import android.content.Context;
import android.os.Build;
import android.os.Process;
import top.niunaijun.blackbox.BlackBoxCore;
import top.niunaijun.blackbox.fake.hook.ClassInvocationStub;
import top.niunaijun.blackbox.utils.Slog;

public class WebViewProxy extends ClassInvocationStub {
    public static final String TAG = "WebViewProxy";

    /* access modifiers changed from: protected */
    public Object getWho() {
        try {
            return Class.forName("android.webkit.WebView");
        } catch (Throwable t) {
            Slog.w(TAG, "getWho: WebView class not found", t);
            return "android.webkit.WebView";
        }
    }

    /* access modifiers changed from: protected */
    public void inject(Object who, Object origin) {
        try {
            ensureWebViewDataDirectorySuffix();
        } catch (Throwable t) {
            Slog.w(TAG, "inject: ensureWebViewDataDirectorySuffix failed", t);
        }
    }

    public boolean isBadEnv() {
        Context ctx;
        try {
            if (BlackBoxCore.get() != null) {
                BlackBoxCore.get();
                ctx = BlackBoxCore.getContext();
            } else {
                ctx = null;
            }
            if (ctx != null) {
                return false;
            }
            Slog.w(TAG, "isBadEnv: BlackBox context is null");
            return true;
        } catch (Throwable t) {
            Slog.w(TAG, "isBadEnv error", t);
            return true;
        }
    }

    private void ensureWebViewDataDirectorySuffix() {
        String suffix;
        if (Build.VERSION.SDK_INT >= 28 && (suffix = buildDataDirectorySuffix()) != null && !suffix.isEmpty()) {
            try {
                Class.forName("android.webkit.WebView").getMethod("setDataDirectorySuffix", new Class[]{String.class}).invoke((Object) null, new Object[]{suffix});
                Slog.d(TAG, "Applied WebView suffix=" + suffix);
            } catch (Throwable t) {
                Slog.w(TAG, "Failed to set WebView suffix", t);
            }
        }
    }

    private String buildDataDirectorySuffix() {
        try {
            int uid = Process.myUid();
            return "blackbox_u" + uid + "_p" + Process.myPid();
        } catch (Throwable th) {
            return null;
        }
    }
}
