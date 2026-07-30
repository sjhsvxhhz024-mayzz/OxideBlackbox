package com.eclipsbox.app;

import android.content.Context;

import com.eclipsbox.app.util.Prefs;

import top.niunaijun.blackbox.app.configuration.ClientConfiguration;

/**
 * Host configuration for the BlackBox core.
 *
 * getHostPackageName() is the only mandatory hook — the core uses it inside
 * doAttachBaseContext() to tell the main host process apart from the :server
 * and virtual :pN processes, so it MUST return the real host applicationId
 * (identical across every process of this app).
 */
public class EclipsClientConfig extends ClientConfiguration {

    private final Context base;

    public EclipsClientConfig(Context base) {
        this.base = base;
    }

    @Override
    public String getHostPackageName() {
        return base.getPackageName();
    }

    @Override
    public boolean isHideRoot() {
        try {
            return new Prefs(base).hideRoot();
        } catch (Throwable t) {
            return true;
        }
    }

    @Override
    public boolean isEnableLauncherActivity() {
        return true;
    }
}
