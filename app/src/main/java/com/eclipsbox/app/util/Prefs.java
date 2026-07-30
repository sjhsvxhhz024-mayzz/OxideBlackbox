package com.eclipsbox.app.util;

import android.content.Context;
import android.content.SharedPreferences;

/** Small typed wrapper over SharedPreferences. Auto Google services defaults ON. */
public class Prefs {
    private static final String FILE = "eclipsbox_prefs";
    private final SharedPreferences sp;

    public Prefs(Context c) {
        sp = c.getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    /** Automatically install Google services into every new clone. Default: true. */
    public boolean autoGms() {
        return sp.getBoolean("auto_gms", true);
    }

    public void setAutoGms(boolean v) {
        sp.edit().putBoolean("auto_gms", v).apply();
    }

    public boolean hideRoot() {
        return sp.getBoolean("hide_root", true);
    }

    public void setHideRoot(boolean v) {
        sp.edit().putBoolean("hide_root", v).apply();
    }

    public boolean onboardingDone() {
        return sp.getBoolean("onboarded", false);
    }

    public void setOnboardingDone(boolean v) {
        sp.edit().putBoolean("onboarded", v).apply();
    }
}
