package com.eclipsbox.app.ui;

import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.GridLayoutManager;

import com.eclipsbox.app.R;
import com.eclipsbox.app.databinding.ActivityMainBinding;
import com.eclipsbox.app.databinding.SheetCloneBinding;
import com.eclipsbox.app.model.AppEntry;
import com.eclipsbox.app.util.Prefs;
import com.google.android.material.bottomsheet.BottomSheetDialog;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

import top.niunaijun.blackbox.BlackBoxCore;
import top.niunaijun.blackbox.entity.pm.InstallResult;

/**
 * EclipsBox home — the grid of virtualized app clones.
 * Tap a clone to launch; long-press for actions (stop / clear / enable Google / remove).
 */
public class MainActivity extends AppCompatActivity {

    /** Default virtual user (BUserHandle.USER_OWNER). */
    public static final int USER = 0;

    private ActivityMainBinding b;
    private CloneAdapter adapter;
    private Prefs prefs;

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final AtomicBoolean gmsBootstrapped = new AtomicBoolean(false);

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        b = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(b.getRoot());
        prefs = new Prefs(this);

        adapter = new CloneAdapter(this::launchClone, this::showActions);
        b.recycler.setLayoutManager(new GridLayoutManager(this, 2));
        b.recycler.setAdapter(adapter);

        b.fabAdd.setOnClickListener(v ->
                startActivity(new Intent(this, AppPickerActivity.class)));

        b.toolbar.inflateMenu(R.menu.main);
        b.toolbar.setOnMenuItemClickListener(this::onMenu);
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadClones();
    }

    private boolean onMenu(@NonNull android.view.MenuItem item) {
        int id = item.getItemId();
        if (id == R.id.action_gms) {
            enableGoogleServices(USER, null);
            return true;
        } else if (id == R.id.action_settings) {
            startActivity(new Intent(this, SettingsActivity.class));
            return true;
        } else if (id == R.id.action_about) {
            new AlertDialog.Builder(this)
                    .setTitle(R.string.app_name)
                    .setMessage(R.string.about_body)
                    .setPositiveButton(android.R.string.ok, null)
                    .show();
            return true;
        }
        return false;
    }

    // ---- data ----

    private void loadClones() {
        io.execute(() -> {
            final List<AppEntry> entries = new ArrayList<>();
            try {
                PackageManager pm = BlackBoxCore.getPackageManager();
                List<ApplicationInfo> apps = BlackBoxCore.get().getInstalledApplications(0, USER);
                if (apps != null) {
                    for (ApplicationInfo ai : apps) {
                        CharSequence label = ai.loadLabel(pm);
                        entries.add(new AppEntry(
                                label == null ? ai.packageName : label.toString(),
                                ai.packageName, ai.sourceDir, safeIcon(pm, ai)));
                    }
                }
            } catch (Throwable t) {
                t.printStackTrace();
            }
            ui.post(() -> {
                adapter.submit(entries);
                boolean empty = entries.isEmpty();
                b.emptyView.setVisibility(empty ? View.VISIBLE : View.GONE);
                b.recycler.setVisibility(empty ? View.GONE : View.VISIBLE);
            });
            maybeBootstrapGms();
        });
    }

    /** Auto-install Google services once per session (guarded, per core recommendation). */
    private void maybeBootstrapGms() {
        if (!prefs.autoGms()) return;
        if (!gmsBootstrapped.compareAndSet(false, true)) return;
        try {
            if (BlackBoxCore.get().isSupportGms() && !BlackBoxCore.get().isInstallGms(USER)) {
                BlackBoxCore.get().installGms(USER);
            }
        } catch (Throwable t) {
            t.printStackTrace();
        }
    }

    private android.graphics.drawable.Drawable safeIcon(PackageManager pm, ApplicationInfo ai) {
        try {
            return ai.loadIcon(pm);
        } catch (Throwable t) {
            return getDrawable(R.mipmap.ic_launcher);
        }
    }

    // ---- actions ----

    private void launchClone(AppEntry e) {
        try {
            if (!BlackBoxCore.get().launchApk(e.packageName, USER)) {
                toast(getString(R.string.launch_fail));
            }
        } catch (Throwable t) {
            t.printStackTrace();
            toast(getString(R.string.launch_fail));
        }
    }

    private void showActions(AppEntry e) {
        BottomSheetDialog dialog = new BottomSheetDialog(this);
        SheetCloneBinding s = SheetCloneBinding.inflate(getLayoutInflater());
        dialog.setContentView(s.getRoot());
        s.sheetIcon.setImageDrawable(e.icon);
        s.sheetName.setText(e.label);

        s.actLaunch.setOnClickListener(v -> { dialog.dismiss(); launchClone(e); });
        s.actStop.setOnClickListener(v -> { dialog.dismiss(); runOn(() ->
                BlackBoxCore.get().stopPackage(e.packageName, USER), getString(R.string.stopped, e.label)); });
        s.actClear.setOnClickListener(v -> { dialog.dismiss(); runOn(() ->
                BlackBoxCore.get().clearPackage(e.packageName, USER), getString(R.string.cleared, e.label)); });
        s.actGoogle.setOnClickListener(v -> { dialog.dismiss(); enableGoogleServices(USER, e.label); });
        s.actUninstall.setOnClickListener(v -> { dialog.dismiss(); confirmRemove(e); });

        dialog.show();
    }

    private void runOn(Runnable coreCall, String okMsg) {
        io.execute(() -> {
            boolean ok = true;
            try { coreCall.run(); } catch (Throwable t) { ok = false; t.printStackTrace(); }
            final boolean done = ok;
            ui.post(() -> { if (done) toast(okMsg); loadClones(); });
        });
    }

    private void confirmRemove(AppEntry e) {
        new AlertDialog.Builder(this)
                .setTitle(e.label)
                .setMessage(R.string.uninstall)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.act_uninstall, (d, w) -> io.execute(() -> {
                    try {
                        BlackBoxCore.get().uninstallPackageAsUser(e.packageName, USER);
                    } catch (Throwable t) {
                        t.printStackTrace();
                    }
                    ui.post(() -> {
                        toast(getString(R.string.uninstalled, e.label));
                        loadClones();
                    });
                }))
                .show();
    }

    private void enableGoogleServices(int user, String forLabel) {
        toast(getString(R.string.gms_running));
        io.execute(() -> {
            String msg;
            try {
                if (!BlackBoxCore.get().isSupportGms()) {
                    msg = getString(R.string.gms_none);
                } else {
                    InstallResult r = BlackBoxCore.get().installGms(user);
                    msg = (r != null && r.success) ? getString(R.string.gms_ok) : getString(R.string.gms_fail);
                }
            } catch (Throwable t) {
                t.printStackTrace();
                msg = getString(R.string.gms_fail);
            }
            final String out = msg;
            ui.post(() -> toast(out));
        });
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }
}
