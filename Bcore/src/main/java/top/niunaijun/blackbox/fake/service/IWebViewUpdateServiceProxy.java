package top.niunaijun.blackbox.fake.service;

import android.content.Context;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import top.niunaijun.blackbox.BlackBoxCore;
import top.niunaijun.blackbox.fake.hook.ClassInvocationStub;
import top.niunaijun.blackbox.utils.Slog;

public class IWebViewUpdateServiceProxy extends ClassInvocationStub {
    public static final String TAG = "IWebViewUpdateServiceProxy";

    public IWebViewUpdateServiceProxy() {}

    @Override
    protected Object getWho() {
        try {
            return Class.forName("android.webkit.IWebViewUpdateService");
        } catch (Throwable t) {
            Slog.w(TAG, "getWho: IWebViewUpdateService not found", t);
            return "android.webkit.IWebViewUpdateService";
        }
    }

    @Override
    protected void inject(Object who, Object origin) {
        // Nothing to call on super (abstract in base class).
        try {
            createSafeFallback();
        } catch (Throwable t) {
            Slog.w(TAG, "inject: fallback failed", t);
        }
    }

    @Override
    public boolean isBadEnv() {
        try {
            Context ctx = BlackBoxCore.get() != null ? BlackBoxCore.get().getContext() : null;
            return ctx == null;
        } catch (Throwable t) {
            return true;
        }
    }

    private void createSafeFallback() {
        try {
            final Class<?> iface = Class.forName("android.webkit.IWebViewUpdateService");
            Object proxy = Proxy.newProxyInstance(
                iface.getClassLoader(),
                new Class<?>[]{iface},
                new InvocationHandler() {
                    @Override
                    public Object invoke(Object p, Method method, Object[] args) {
                        if (method.getReturnType().isArray()) {
                            return java.lang.reflect.Array.newInstance(method.getReturnType().getComponentType(), 0);
                        }
                        if (method.getReturnType() == boolean.class || method.getReturnType() == Boolean.class) {
                            return false;
                        }
                        return null;
                    }
                }
            );
            Slog.d(TAG, "Safe IWebViewUpdateService proxy created: " + proxy.getClass().getName());
        } catch (Throwable t) {
            Slog.w(TAG, "createSafeFallback failed", t);
        }
    }
}
