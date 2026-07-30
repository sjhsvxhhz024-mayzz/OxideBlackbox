package top.niunaijun.blackbox.fake.service;

import android.Manifest;
import android.app.ActivityManager;
import android.app.IServiceConnection;
import android.content.ComponentName;
import android.content.Context;
import android.content.IIntentReceiver;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ProviderInfo;
import android.content.pm.ResolveInfo;
import android.os.IBinder;
import android.os.IInterface;
import android.util.Log;

import java.lang.ref.WeakReference;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Objects;

import black.android.app.BRActivityManagerNative;
import black.android.app.BRActivityManagerOreo;
import black.android.app.BRLoadedApkReceiverDispatcher;
import black.android.app.BRLoadedApkReceiverDispatcherInnerReceiver;
import black.android.app.BRLoadedApkServiceDispatcher;
import black.android.app.BRLoadedApkServiceDispatcherInnerConnection;
import black.android.content.BRContentProviderNative;
import black.android.content.pm.BRUserInfo;
import black.android.util.BRSingleton;
import top.niunaijun.blackbox.BlackBoxCore;
import top.niunaijun.blackbox.app.BActivityThread;
import top.niunaijun.blackbox.core.env.AppSystemEnv;
import top.niunaijun.blackbox.entity.AppConfig;
import top.niunaijun.blackbox.entity.am.RunningAppProcessInfo;
import top.niunaijun.blackbox.entity.am.RunningServiceInfo;
import top.niunaijun.blackbox.fake.delegate.ContentProviderDelegate;
import top.niunaijun.blackbox.fake.delegate.InnerReceiverDelegate;
import top.niunaijun.blackbox.fake.delegate.ServiceConnectionDelegate;
import top.niunaijun.blackbox.fake.frameworks.BActivityManager;
import top.niunaijun.blackbox.fake.frameworks.BPackageManager;
import top.niunaijun.blackbox.fake.hook.ClassInvocationStub;
import top.niunaijun.blackbox.fake.hook.MethodHook;
import top.niunaijun.blackbox.fake.hook.ProxyMethod;
import top.niunaijun.blackbox.fake.hook.ScanClass;
import top.niunaijun.blackbox.fake.service.base.PkgMethodProxy;
import top.niunaijun.blackbox.fake.service.context.providers.ContentProviderStub;
import top.niunaijun.blackbox.proxy.ProxyManifest;
import top.niunaijun.blackbox.proxy.record.ProxyBroadcastRecord;
import top.niunaijun.blackbox.proxy.record.ProxyPendingRecord;
import top.niunaijun.blackbox.utils.MethodParameterUtils;
import top.niunaijun.blackbox.utils.Reflector;
import top.niunaijun.blackbox.utils.compat.ActivityManagerCompat;
import top.niunaijun.blackbox.utils.compat.BuildCompat;
import top.niunaijun.blackbox.utils.compat.ParceledListSliceCompat;
import top.niunaijun.blackbox.utils.compat.TaskDescriptionCompat;

import static android.content.Context.RECEIVER_EXPORTED;
import static android.content.Context.RECEIVER_NOT_EXPORTED;
import static android.content.pm.PackageManager.GET_META_DATA;
import static android.content.pm.PackageManager.PERMISSION_GRANTED;

/**
 * Created by Milk on 3/30/21.
 * * ∧＿∧
 * (`･ω･∥
 * 丶　つ０
 * しーＪ
 * 此处无Bug
 */
@ScanClass(ActivityManagerCommonProxy.class)
public class IActivityManagerProxy extends ClassInvocationStub {
    public static final String TAG = "ActivityManagerStub";

    @Override
    protected Object getWho() {
        Object iActivityManager = null;
        if (BuildCompat.isOreo()) {
            iActivityManager = BRActivityManagerOreo.get().IActivityManagerSingleton();
        } else if (BuildCompat.isL()) {
            iActivityManager = BRActivityManagerNative.get().gDefault();
        }
        return BRSingleton.get(iActivityManager).get();
    }

    @Override
    protected void inject(Object base, Object proxy) {
        Object iActivityManager = null;
        if (BuildCompat.isOreo()) {
            iActivityManager = BRActivityManagerOreo.get().IActivityManagerSingleton();
        } else if (BuildCompat.isL()) {
            iActivityManager = BRActivityManagerNative.get().gDefault();
        }
        BRSingleton.get(iActivityManager)._set_mInstance(proxy);
    }

    @Override
    public boolean isBadEnv() {
        return getProxyInvocation() != getWho();
    }

    @Override
    protected void onBindMethod() {
        super.onBindMethod();
        addMethodHook(new PkgMethodProxy("getAppStartMode"));
        addMethodHook(new PkgMethodProxy("setAppLockedVerifying"));
        addMethodHook(new PkgMethodProxy("reportJunkFromApp"));
    }
/*
   @ProxyMethod("getContentProvider")
public static class GetContentProvider extends MethodHook {

    // 🔹 authority index resolver (Android 9+ safe)
    private int getAuthIndex() {
        // getContentProvider(callingPkg, authority, userId, stable)
        return BuildCompat.isQ() ? 1 : 0;
    }

    // 🔹 userId index resolver
    private int getUserIndex() {
        // usually last or second last
        return BuildCompat.isQ() ? 2 : 1;
    }

    @Override
    protected Object hook(Object who, Method method, Object[] args) throws Throwable {

        int authIndex = getAuthIndex();
        Object auth = args[authIndex];

        if (!(auth instanceof String)) {
            return method.invoke(who, args);
        }

        String authority = (String) auth;

        // ✅ System providers → never virtualize
        if ("settings".equals(authority)
                || "media".equals(authority)
                || "telephony".equals(authority)) {

            Object content = method.invoke(who, args);
            if (content != null) {
                ContentProviderDelegate.update(content, authority);
            }
            return content;
        }

        // ✅ Google / GMS providers → system handle
        if (authority.startsWith("com.google.android.gms")) {
            return method.invoke(who, args);
        }

        // 🔹 resolve from virtual PM
        ProviderInfo providerInfo =
                BlackBoxCore.getBPackageManager()
                        .resolveContentProvider(
                                authority,
                                GET_META_DATA,
                                BActivityThread.getUserId()
                        );

        // ❗ CRITICAL NPE FIX
        if (providerInfo == null) {
            return method.invoke(who, args);
        }

        AppConfig appConfig =
                BlackBoxCore.getBActivityManager()
                        .initProcess(
                                providerInfo.packageName,
                                providerInfo.processName,
                                BActivityThread.getUserId()
                        );

        if (appConfig == null) {
            return method.invoke(who, args);
        }

        // 🔹 replace authority + user
        args[authIndex] = ProxyManifest.getProxyAuthorities(appConfig.bpid);
        args[getUserIndex()] = BlackBoxCore.getHostUserId();

        Object content = method.invoke(who, args);
        if (content == null) return null;

        Reflector.with(content)
                .field("info")
                .set(providerInfo);

        IBinder providerBinder =
                BlackBoxCore.getBActivityManager()
                        .acquireContentProviderClient(providerInfo);

        if (providerBinder != null) {
            Reflector.with(content)
                    .field("provider")
                    .set(
                            new ContentProviderStub().wrapper(
                                    BRContentProviderNative.get()
                                            .asInterface(providerBinder),
                                    BActivityThread.getAppPackageName()
                            )
                    );
        }

        return content;
    }
}
    /////
    @ProxyMethod("getContentProvider")
public static class GetContentProvider extends MethodHook {

    private int getAuthIndex() {
        return BuildCompat.isQ() ? 2 : 1;
    }

    private int getUserIndex() {
        return getAuthIndex() + 1;
    }

    @Override
    public Object hook(Object who, Method method, Object[] args) throws Throwable {

        int authIndex = getAuthIndex();
        Object authObj = args[authIndex];

        // ✅ SAFE: auth must be String
        if (!(authObj instanceof String)) {
            MethodParameterUtils.replaceLastUserId(args);
            return method.invoke(who, args);
        }

        String authority = (String) authObj;

        // ✅ Proxy authority → system handle
        if (ProxyManifest.isProxy(authority)) {
            MethodParameterUtils.replaceLastUserId(args);
            return method.invoke(who, args);
        }

        // ✅ Android 10+
        if (BuildCompat.isQ()) {
            args[1] = BlackBoxCore.getHostPkg();
        }

        // ===== system providers =====
        if ("settings".equals(authority)
                || "media".equals(authority)
                || "telephony".equals(authority)) {

            Object content = method.invoke(who, args);
            if (content != null) {
                ContentProviderDelegate.update(content, authority);
            }
            return content;
        }

        // ===== resolve provider safely =====
        ProviderInfo providerInfo =
                BlackBoxCore.getBPackageManager()
                        .resolveContentProvider(authority, GET_META_DATA,
                                BActivityThread.getUserId());

        // ✅ FIX: provider may be NULL (GMS Dynamite)
        if (providerInfo == null) {
            MethodParameterUtils.replaceLastUserId(args);
            return method.invoke(who, args);
        }

        if (!providerInfo.enabled) {
            return null;
        }

        IBinder providerBinder = null;

        if (BActivityThread.getAppPid() != -1) {
            AppConfig appConfig =
                    BlackBoxCore.getBActivityManager()
                            .initProcess(
                                    providerInfo.packageName,
                                    providerInfo.processName,
                                    BActivityThread.getUserId()
                            );

            if (appConfig != null && appConfig.bpid != BActivityThread.getAppPid()) {
                providerBinder =
                        BlackBoxCore.getBActivityManager()
                                .acquireContentProviderClient(providerInfo);
            }

            args[authIndex] = ProxyManifest.getProxyAuthorities(appConfig.bpid);
            args[getUserIndex()] = BlackBoxCore.getHostUserId();
        }

        if (providerBinder == null) {
            return null;
        }

        Object content = method.invoke(who, args);
        if (content == null) {
            return null;
        }

        // ✅ inject provider info
        Reflector.with(content)
                .field("info")
                .set(providerInfo);

        Reflector.with(content)
                .field("provider")
                .set(new ContentProviderStub()
                        .wrapper(
                                BRContentProviderNative.get().asInterface(providerBinder),
                                BActivityThread.getAppPackageName()
                        ));

        MethodParameterUtils.replaceLastUserId(args);
        return content;
    }
}*/
    
    @ProxyMethod("getContentProvider")
public static class GetContentProvider extends MethodHook {

    private int getAuthIndex() {
        return BuildCompat.isQ() ? 2 : 1;
    }

    private int getUserIndex() {
        return getAuthIndex() + 1;
    }

    @Override
    public Object hook(Object who, Method method, Object[] args) throws Throwable {

        int authIndex = getAuthIndex();
        Object authObj = args[authIndex];

        // ---------- SAFETY ----------
        if (!(authObj instanceof String)) {
            MethodParameterUtils.replaceLastUserId(args);
            return method.invoke(who, args);
        }

        String authority = (String) authObj;

        // ---------- proxy authority ----------
        if (ProxyManifest.isProxy(authority)) {
            MethodParameterUtils.replaceLastUserId(args);
            return method.invoke(who, args);
        }

        // ---------- Android 10+ ----------
        if (BuildCompat.isQ()) {
            args[1] = BlackBoxCore.getHostPkg();
        }

        // ---------- system providers ----------
        if ("settings".equals(authority)
                || "media".equals(authority)
                || "telephony".equals(authority)) {

            Object content = method.invoke(who, args);
            if (content != null) {
                ContentProviderDelegate.update(content, authority);
            }
            return content;
        }

        // ---------- resolve provider ----------
        ProviderInfo providerInfo =
                BlackBoxCore.getBPackageManager()
                        .resolveContentProvider(
                                authority,
                                GET_META_DATA,
                                BActivityThread.getUserId()
                        );

        // ✅ CRITICAL FIX #1 (GMS / Dynamite)
      /*  if (providerInfo == null || providerInfo.packageName == null) {
          //  MethodParameterUtils.replaceLastUserId(args);
            return method.invoke(who, args);
        }*/
            // ✅ CRITICAL FIX #1 (GMS / Dynamite / Twitter / Facebook SAFE)
if (providerInfo == null || providerInfo.packageName == null) {

    // Android 10+ requires calling package fix
    if (BuildCompat.isQ()) {
        args[1] = BlackBoxCore.getHostPkg();
    }

    // Always fix userId before system invoke
    MethodParameterUtils.replaceLastUserId(args);

    return method.invoke(who, args);
}

        if (!providerInfo.enabled) {
            return null;
        }

        IBinder providerBinder = null;

        if (BActivityThread.getAppPid() != -1) {

            AppConfig appConfig =
                    BlackBoxCore.getBActivityManager()
                            .initProcess(
                                    providerInfo.packageName,
                                    providerInfo.processName,
                                    BActivityThread.getUserId()
                            );

            // ✅ CRITICAL FIX #2
            if (appConfig == null) {
                MethodParameterUtils.replaceLastUserId(args);
                return method.invoke(who, args);
            }

            if (appConfig.bpid != BActivityThread.getAppPid()) {
                providerBinder =
                        BlackBoxCore.getBActivityManager()
                                .acquireContentProviderClient(providerInfo);
            }

            args[authIndex] = ProxyManifest.getProxyAuthorities(appConfig.bpid);
            args[getUserIndex()] = BlackBoxCore.getHostUserId();
        }

        // ✅ CRITICAL FIX #3 (never return null for GMS)
        if (providerBinder == null) {
            MethodParameterUtils.replaceLastUserId(args);
            return method.invoke(who, args);
        }

        Object content = method.invoke(who, args);
        if (content == null) {
            return null;
        }

        // ---------- inject ----------
        Reflector.with(content)
                .field("info")
                .set(providerInfo);

        Reflector.with(content)
                .field("provider")
                .set(
                        new ContentProviderStub().wrapper(
                                BRContentProviderNative.get()
                                        .asInterface(providerBinder),
                                BActivityThread.getAppPackageName()
                        )
                );

        MethodParameterUtils.replaceLastUserId(args);
        return content;
    }
}

    @ProxyMethod("startService")
    public static class StartService extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            Intent intent = (Intent) args[1];
            String resolvedType = (String) args[2];
            ResolveInfo resolveInfo = BlackBoxCore.getBPackageManager().resolveService(intent, 0, resolvedType, BActivityThread.getUserId());
            if (resolveInfo == null) {
                return method.invoke(who, args);
            }

            int requireForegroundIndex = getRequireForeground();
            boolean requireForeground = false;
            if (requireForegroundIndex != -1) {
                requireForeground = (boolean) args[requireForegroundIndex];
            }
            return BlackBoxCore.getBActivityManager().startService(intent, resolvedType, requireForeground, BActivityThread.getUserId());
        }

        public int getRequireForeground() {
            if (BuildCompat.isOreo()) {
                return 3;
            }
            return -1;
        }
    }

    @ProxyMethod("stopService")
    public static class StopService extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            Intent intent = (Intent) args[1];
            String resolvedType = (String) args[2];
            return BlackBoxCore.getBActivityManager().stopService(intent, resolvedType, BActivityThread.getUserId());
        }
    }

    @ProxyMethod("stopServiceToken")
    public static class StopServiceToken extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            ComponentName componentName = (ComponentName) args[0];
            IBinder token = (IBinder) args[1];
            BlackBoxCore.getBActivityManager().stopServiceToken(componentName, token, BActivityThread.getUserId());
            return true;
        }
    }
    
    static IServiceConnection  StartService;
    
    
    public static Object BindServiceCommon(Object who, Method method, Object[] args, int callingPackageIndex) throws Throwable {
		IInterface iInterface = (IInterface) args[0];
		IBinder iBinder = (IBinder) args[1];
		Intent intent = (Intent) args[2];
		String resolvedType = (String) args[3];
		IServiceConnection connection = (IServiceConnection) args[4];

		ComponentName component = intent.getComponent();
		long flags = getIntOrLongValue(args[5]);

		int userId = intent.getIntExtra("_B_|_UserId", -1);
		userId = userId == -1 ? BActivityThread.getUserId() : userId;

		ResolveInfo resolveInfo = BlackBoxCore.getBPackageManager().resolveService(intent, 0, resolvedType, userId);

		if (component != null && component.getPackageName().equals(BlackBoxCore.getHostPkg())) {
			return method.invoke(who, args);
		}

		int callingPkgIdx = isIsolated() ? 7 : 6;
		if (args.length > callingPkgIdx && (args[callingPkgIdx] instanceof String)) {
			args[callingPkgIdx] = BlackBoxCore.getHostPkg();
		}

		if (resolveInfo == null) {
			if (component == null || !AppSystemEnv.isOpenPackage(component.getPackageName())) {
				Log.e("ActivityManager", "Block bindService: " + intent);
				return 0;
			}
			MethodParameterUtils.replaceLastUserId(args);
			return method.invoke(who, args);
		}

		if ((flags & (-2147483648L)) != 0) {
			args[5] = (flags & 2147483647L);
		}

		AppConfig appConfig = BActivityManager.get().initProcess(
            resolveInfo.serviceInfo.packageName,
            resolveInfo.serviceInfo.name,
            userId);

		if (appConfig == null) {
			Log.e("ActivityManager", "failed to initProcess for bindService: " + component);
			return 0;
		}

		Intent proxyIntent = BlackBoxCore.getBActivityManager().bindService(
            intent,
            connection == null ? null : connection.asBinder(),
            resolvedType,
            userId);

		args[2] = proxyIntent;
		args[4] = ServiceConnectionDelegate.createProxy(connection, intent);

		WeakReference<?> weakReference = BRLoadedApkServiceDispatcherInnerConnection.get(connection).mDispatcher();
		if (weakReference != null && weakReference.get() != null) {
			BRLoadedApkServiceDispatcher.get(weakReference.get())
                ._set_mConnection(ServiceConnectionDelegate.createProxy(connection, intent));
		}

		return method.invoke(who, args);
	}

	private static boolean isIsolated() {
		return false;
	}

	private static long getIntOrLongValue(Object obj) {
		if (obj instanceof Number) {
			return ((Number) obj).longValue();
		}
		return 0L;
	}

	@ProxyMethod("bindService")
	public static class BindService extends MethodHook {

		@Override
		protected Object hook(Object who, Method method, Object[] args) throws Throwable {
			return BindServiceCommon(who, method, args, 6);
		}

		@Override
		protected boolean isEnable() {
			return BlackBoxCore.get().isBlackProcess() || BlackBoxCore.get().isServerProcess();
		}
	}
    
    // android 14 add
    @ProxyMethod("bindServiceInstance")
    public static class bindServiceInstance extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return BindServiceCommon(who,method,args,7);
        }

        @Override
        protected boolean isEnable() {
            return BlackBoxCore.get().isBlackProcess() || BlackBoxCore.get().isServerProcess();
        }
    }

    // 10.0
    @ProxyMethod("bindIsolatedService")
    public static class BindIsolatedService extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            // instanceName
            args[6] = null;
            return BindServiceCommon(who,method,args,7);
        }

        @Override
        protected boolean isEnable() {
            return BlackBoxCore.get().isBlackProcess() || BlackBoxCore.get().isServerProcess();
        }
    }

    @ProxyMethod("unbindService")
    public static class UnbindService extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            IServiceConnection iServiceConnection = (IServiceConnection) args[0];
            if (iServiceConnection == null) {
                return method.invoke(who, args);
            }
            BlackBoxCore.getBActivityManager().unbindService(iServiceConnection.asBinder(), BActivityThread.getUserId());
            ServiceConnectionDelegate delegate = ServiceConnectionDelegate.getDelegate(iServiceConnection.asBinder());
            if (delegate != null) {
                args[0] = delegate;
            }
            return method.invoke(who, args);
        }
    }

    @ProxyMethod("getRunningAppProcesses")
    public static class GetRunningAppProcesses extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            RunningAppProcessInfo runningAppProcesses = BActivityManager.get().getRunningAppProcesses(BActivityThread.getAppPackageName(), BActivityThread.getUserId());
            if (runningAppProcesses == null) {
                return new ArrayList<>();
            }
            return runningAppProcesses.mAppProcessInfoList;
        }
    }

    @ProxyMethod("getServices")
    public static class GetServices extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            RunningServiceInfo runningServices = BActivityManager.get().getRunningServices(BActivityThread.getAppPackageName(), BActivityThread.getUserId());
            if (runningServices == null) {
                return new ArrayList<>();
            }
            return runningServices.mRunningServiceInfoList;
        }
    }

    @ProxyMethod("getIntentSender")
    public static class GetIntentSender extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            int type = (int) args[0];
            Intent[] intents = (Intent[]) args[getIntentsIndex(args)];
            MethodParameterUtils.replaceFirstAppPkg(args);

            for (int i = 0; i < intents.length; i++) {
                Intent intent = intents[i];
                switch (type) {
                    case ActivityManagerCompat.INTENT_SENDER_ACTIVITY:
                        Intent shadow = new Intent();
                        shadow.setComponent(new ComponentName(BlackBoxCore.getHostPkg(), ProxyManifest.getProxyPendingActivity(BActivityThread.getAppPid())));
                        ProxyPendingRecord.saveStub(shadow, intent, BActivityThread.getUserId());
                        intents[i] = shadow;
                        break;
                }
            }
            IInterface invoke = (IInterface) method.invoke(who, args);
            if (invoke != null) {
                String[] packagesForUid = BPackageManager.get().getPackagesForUid(BActivityThread.getCallingBUid());
                if (packagesForUid.length < 1) {
                    packagesForUid = new String[]{BlackBoxCore.getHostPkg()};
                }
                BlackBoxCore.getBActivityManager().getIntentSender(invoke.asBinder(), packagesForUid[0], BActivityThread.getCallingBUid());
            }
            return invoke;
        }

        private int getIntentsIndex(Object[] args) {
            for (int i = 0; i < args.length; i++) {
                if (args[i] instanceof Intent[]) {
                    return i;
                }
            }
            if (BuildCompat.isR()) {
                return 6;
            } else {
                return 5;
            }
        }
    }

    @ProxyMethod("getPackageForIntentSender")
    public static class getPackageForIntentSender extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            IInterface invoke = (IInterface) args[0];
            return BlackBoxCore.getBActivityManager().getPackageForIntentSender(invoke.asBinder());
        }
    }

    @ProxyMethod("getUidForIntentSender")
    public static class getUidForIntentSender extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            IInterface invoke = (IInterface) args[0];
            return BlackBoxCore.getBActivityManager().getUidForIntentSender(invoke.asBinder());
        }
    }

    @ProxyMethod("getIntentSenderWithSourceToken")
    public static class GetIntentSenderWithSourceToken extends GetIntentSender {
    }

    @ProxyMethod("getIntentSenderWithFeature")
    public static class GetIntentSenderWithFeature extends GetIntentSender {
    }

    @ProxyMethod("broadcastIntentWithFeature")
    public static class BroadcastIntentWithFeature extends BroadcastIntent {
    }

    @ProxyMethod("broadcastIntent")
    public static class BroadcastIntent extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            int intentIndex = getIntentIndex(args);
            Intent intent = (Intent) args[intentIndex];
            String resolvedType = (String) args[intentIndex + 1];
            Intent proxyIntent = BlackBoxCore.getBActivityManager().sendBroadcast(intent, resolvedType, BActivityThread.getUserId());
            if (proxyIntent != null) {
                proxyIntent.setExtrasClassLoader(BActivityThread.getApplication().getClassLoader());
                ProxyBroadcastRecord.saveStub(proxyIntent, intent, BActivityThread.getUserId());
                args[intentIndex] = proxyIntent;
            }
            // ignore permission
            for (int i = 0; i < args.length; i++) {
                Object o = args[i];
                if (o instanceof String[]) {
                    args[i] = null;
                }
            }
            return method.invoke(who, args);
        }

        int getIntentIndex(Object[] args) {
            for (int i = 0; i < args.length; i++) {
                Object arg = args[i];
                if (arg instanceof Intent) {
                    return i;
                }
            }
            return 1;
        }
    }

    @ProxyMethod("unregisterReceiver")
    public static class unregisterReceiver extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return method.invoke(who, args);
        }
    }

    @ProxyMethod("finishReceiver")
    public static class finishReceiver extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return method.invoke(who, args);
        }
    }

    @ProxyMethod("publishService")
    public static class PublishService extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return method.invoke(who, args);
        }
    }

    @ProxyMethod("peekService")
    public static class PeekService extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            MethodParameterUtils.replaceLastAppPkg(args);
            Intent intent = (Intent) args[0];
            String resolvedType = (String) args[1];
            IBinder peek = BlackBoxCore.getBActivityManager().peekService(intent, resolvedType, BActivityThread.getUserId());
            return peek;
        }
    }

    // todo
    @ProxyMethod("sendIntentSender")
    public static class SendIntentSender extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return 0;
        }
    }

    // android 11 add
    @ProxyMethod("registerReceiverWithFeature")
    public static class RegisterReceiverWithFeature extends MethodHook{
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            MethodParameterUtils.replaceFirstAppPkg(args);
            int receiverIndex = getReceiverIndex();
            if (args[receiverIndex] != null) {
                IIntentReceiver intentReceiver = (IIntentReceiver) args[receiverIndex];
                IIntentReceiver proxy = InnerReceiverDelegate.createProxy(intentReceiver);

                WeakReference<?> weakReference = BRLoadedApkReceiverDispatcherInnerReceiver.get(intentReceiver).mDispatcher();
                if (weakReference != null) {
                    BRLoadedApkReceiverDispatcher.get(weakReference.get())._set_mIIntentReceiver(proxy);
                }

                args[receiverIndex] = proxy;
            }
            // ignore permission
            if (args[getPermissionIndex()] != null) {
                args[getPermissionIndex()] = null;
            }

            if (BuildCompat.isU()) {
                int flagsIndex = args.length - 1;
                int flags = (int)args[flagsIndex];
                if((flags & RECEIVER_NOT_EXPORTED) == 0 && (flags & RECEIVER_EXPORTED) == 0){
                    flags |= RECEIVER_NOT_EXPORTED;
                }
                args[flagsIndex] = flags;
            }

            return method.invoke(who, args);
        }

        public int getReceiverIndex() {
            if (BuildCompat.isS()) {
                return 4;
            }
            return 3;
        }

        public int getPermissionIndex() {
            if (BuildCompat.isS()) {
                return 6;
            }
            return 5;
        }
    }

    //maxTargetSdk=29
    @ProxyMethod("registerReceiver")
    public static class RegisterReceiver extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            MethodParameterUtils.replaceFirstAppPkg(args);
            int receiverIndex = 2;
            if (args[receiverIndex] != null) {
                IIntentReceiver intentReceiver = (IIntentReceiver) args[receiverIndex];
                IIntentReceiver proxy = InnerReceiverDelegate.createProxy(intentReceiver);

                WeakReference<?> weakReference = BRLoadedApkReceiverDispatcherInnerReceiver.get(intentReceiver).mDispatcher();
                if (weakReference != null) {
                    BRLoadedApkReceiverDispatcher.get(weakReference.get())._set_mIIntentReceiver(proxy);
                }

                args[receiverIndex] = proxy;
            }
            int permissionIndex = 4;
            // ignore permission
            if (args[permissionIndex] != null) {
                args[permissionIndex] = null;
            }
            return method.invoke(who, args);
        }
    }

    @ProxyMethod("grantUriPermission")
    public static class GrantUriPermission extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            MethodParameterUtils.replaceLastUid(args);
            return method.invoke(who, args);
        }
    }

    @ProxyMethod("setServiceForeground")
    public static class setServiceForeground extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
//            if (args[0] instanceof ComponentName) {
//                args[0] = new ComponentName(BlackBoxCore.getHostPkg(), ProxyManifest.getProxyService(BActivityThread.getAppPid()));
//            }
//            return method.invoke(who, args);
            return 0;
        }
    }

    @ProxyMethod("getHistoricalProcessExitReasons")
    public static class getHistoricalProcessExitReasons extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return ParceledListSliceCompat.create(new ArrayList<>());
        }
    }

    @ProxyMethod("getCurrentUser")
    public static class getCurrentUser extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            Object blackBox = BRUserInfo.get()._new(BActivityThread.getUserId(), "BlackBox", BRUserInfo.get().FLAG_PRIMARY());
            return blackBox;
        }
    }

    @ProxyMethod("checkPermission")
    public static class checkPermission extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            MethodParameterUtils.replaceLastUid(args);
            String permission = (String) args[0];
            if (permission.equals(Manifest.permission.ACCOUNT_MANAGER)
                    || permission.equals(Manifest.permission.SEND_SMS)) {
                return PackageManager.PERMISSION_GRANTED;
            }
            return method.invoke(who, args);
        }
    }

    @ProxyMethod("checkUriPermission")
    public static class checkUriPermission extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return PERMISSION_GRANTED;
        }
    }

    // for < Android 10
    @ProxyMethod("setTaskDescription")
    public static class SetTaskDescription extends MethodHook {
        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            ActivityManager.TaskDescription td = (ActivityManager.TaskDescription) args[1];
            args[1] = TaskDescriptionCompat.fix(td);
            return method.invoke(who, args);
        }
    }

    @ProxyMethod("setRequestedOrientation")
    public static class setRequestedOrientation extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            try {
                return method.invoke(who, args);
            } catch (Throwable e) {
                e.printStackTrace();
            }
            return 0;
        }
    }

    @ProxyMethod("registerUidObserver")
    public static class registerUidObserver extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return 0;
        }
    }

    @ProxyMethod("unregisterUidObserver")
    public static class unregisterUidObserver extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return 0;
        }
    }

    @ProxyMethod("updateConfiguration")
    public static class updateConfiguration extends MethodHook {

        @Override
        protected Object hook(Object who, Method method, Object[] args) throws Throwable {
            return 0;
        }
    }
}
