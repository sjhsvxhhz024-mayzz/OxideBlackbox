package com.eclipsbox.app;

import android.app.Application;
import android.content.Context;

import top.niunaijun.blackbox.BlackBoxCore;

/**
 * EclipsBox host application.
 *
 * The BlackBox virtualization core must be wired into the very first lifecycle
 * hooks of the host process: doAttachBaseContext() decides which kind of process
 * this is (main / :server / virtual :pN) and installs the hook framework, and
 * doCreate() finishes bringing the core up. Both MUST run before any of our own
 * code touches the virtualized environment.
 */
public class EclipsApp extends Application {

    private static EclipsApp sInstance;

    public static EclipsApp getInstance() {
        return sInstance;
    }

    @Override
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(base);
        sInstance = this;
        BlackBoxCore.get().doAttachBaseContext(base, new EclipsClientConfig(base));
    }

    @Override
    public void onCreate() {
        super.onCreate();
        BlackBoxCore.get().doCreate();
    }
}
