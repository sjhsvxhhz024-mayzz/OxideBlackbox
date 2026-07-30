package com.eclipsbox.app.ui;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.eclipsbox.app.R;
import com.eclipsbox.app.databinding.ActivitySettingsBinding;
import com.eclipsbox.app.util.Prefs;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import top.niunaijun.blackbox.BlackBoxCore;
import top.niunaijun.blackbox.entity.pm.InstallResult;

public class SettingsActivity extends AppCompatActivity {

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ActivitySettingsBinding b = ActivitySettingsBinding.inflate(getLayoutInflater());
        setContentView(b.getRoot());

        Prefs prefs = new Prefs(this);
        b.toolbar.setNavigationOnClickListener(v -> finish());

        b.switchAutoGms.setChecked(prefs.autoGms());
        b.switchAutoGms.setOnCheckedChangeListener((v, checked) -> prefs.setAutoGms(checked));

        b.switchHideRoot.setChecked(prefs.hideRoot());
        b.switchHideRoot.setOnCheckedChangeListener((v, checked) -> prefs.setHideRoot(checked));

        b.rowReinstallGms.setOnClickListener(v -> reinstallGms());
        b.rowAbout.setOnClickListener(v ->
                Toast.makeText(this, R.string.about_body, Toast.LENGTH_LONG).show());
    }

    private void reinstallGms() {
        Toast.makeText(this, R.string.gms_running, Toast.LENGTH_SHORT).show();
        io.execute(() -> {
            String msg;
            try {
                if (!BlackBoxCore.get().isSupportGms()) {
                    msg = getString(R.string.gms_none);
                } else {
                    InstallResult r = BlackBoxCore.get().installGms(MainActivity.USER);
                    msg = (r != null && r.success) ? getString(R.string.gms_ok) : getString(R.string.gms_fail);
                }
            } catch (Throwable t) {
                msg = getString(R.string.gms_fail);
            }
            final String out = msg;
            ui.post(() -> Toast.makeText(this, out, Toast.LENGTH_SHORT).show());
        });
    }
}
