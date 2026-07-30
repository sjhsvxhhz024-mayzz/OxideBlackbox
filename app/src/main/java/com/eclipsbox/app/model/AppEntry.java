package com.eclipsbox.app.model;

import android.graphics.drawable.Drawable;

/** Lightweight view-model for one app row (host app to clone, or an installed clone). */
public class AppEntry {
    public final String label;
    public final String packageName;
    public final String sourceDir;
    public final Drawable icon;

    public AppEntry(String label, String packageName, String sourceDir, Drawable icon) {
        this.label = label;
        this.packageName = packageName;
        this.sourceDir = sourceDir;
        this.icon = icon;
    }
}
