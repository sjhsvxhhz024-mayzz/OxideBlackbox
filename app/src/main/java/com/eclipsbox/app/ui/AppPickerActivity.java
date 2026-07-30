package com.eclipsbox.app.ui;

import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;

import com.eclipsbox.app.R;
import com.eclipsbox.app.databinding.ActivityAppPickerBinding;
import com.eclipsbox.app.model.AppEntry;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import top.niunaijun.blackbox.BlackBoxCore;
import top.niunaijun.blackbox.entity.pm.InstallResult;
import top.niunaijun.blackbox.utils.AbiUtils;

/**
 * Lists host apps that can be cloned into the EclipsBox virtual space.
 * Follows the BlackBox canon: enumerate the host PackageManager, drop system
 * apps and ABI-incompatible packages, then installPackageAsUser(packageName, USER).
 */
public class AppPickerActivity extends AppCompatActivity {

    private ActivityAppPickerBinding b;
    private AppPickerAdapter adapter;

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        b = ActivityAppPickerBinding.inflate(getLayoutInflater());
        setContentView(b.getRoot());

        b.toolbar.setNavigationOnClickListener(v -> finish());

        adapter = new AppPickerAdapter(this::clone);
        b.recycler.setLayoutManager(new LinearLayoutManager(this));
        b.recycler.setAdapter(adapter);

        loadHostApps();
    }

    private void loadHostApps() {
        setBusy(true);
        io.execute(() -> {
            final List<AppEntry> entries = new ArrayList<>();
            try {
                PackageManager pm = BlackBoxCore.getPackageManager();
                String self = getPackageName();
                List<ApplicationInfo> apps = pm.getInstalledApplications(0);
                for (ApplicationInfo ai : apps) {
                    if (ai.packageName.equals(self)) continue;
                    if ((ai.flags & ApplicationInfo.FLAG_SYSTEM) != 0) continue;
                    if (ai.sourceDir == null) continue;
                    if (!AbiUtils.isSupport(new File(ai.sourceDir))) continue;
                    CharSequence label = ai.loadLabel(pm);
                    entries.add(new AppEntry(
                            label == null ? ai.packageName : label.toString(),
                            ai.packageName,
                            ai.sourceDir,
                            ai.loadIcon(pm)));
                }
                Collections.sort(entries, (x, y) ->
                        x.label.compareToIgnoreCase(y.label));
            } catch (Throwable t) {
                t.printStackTrace();
            }
            ui.post(() -> {
                setBusy(false);
                adapter.submit(entries);
                b.emptyView.setVisibility(entries.isEmpty() ? View.VISIBLE : View.GONE);
            });
        });
    }

    private void clone(AppEntry e) {
        setBusy(true);
        toast(getString(R.string.installing, e.label));
        io.execute(() -> {
            String msg;
            boolean ok = false;
            try {
                InstallResult r = BlackBoxCore.get().installPackageAsUser(e.packageName, MainActivity.USER);
                ok = r != null && r.success;
                msg = ok ? getString(R.string.install_ok, e.label)
                         : getString(R.string.install_fail, r != null && r.msg != null ? r.msg : "unknown");
            } catch (Throwable t) {
                t.printStackTrace();
                msg = getString(R.string.install_fail, t.getMessage());
            }
            final String out = msg;
            final boolean done = ok;
            ui.post(() -> {
                setBusy(false);
                toast(out);
                if (done) {
                    setResult(RESULT_OK);
                    finish();
                }
            });
        });
    }

    private void setBusy(boolean busy) {
        b.progress.setVisibility(busy ? View.VISIBLE : View.GONE);
        b.recycler.setAlpha(busy ? 0.3f : 1f);
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }
}
