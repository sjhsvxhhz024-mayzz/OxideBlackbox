package com.eclipsbox.app.ui;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;

import androidx.appcompat.app.AppCompatActivity;

import com.eclipsbox.app.databinding.ActivitySplashBinding;
import com.eclipsbox.app.util.Prefs;

/** Branded entry point. Shows the eclipse logo, then routes to onboarding or home. */
@SuppressLint("CustomSplashScreen")
public class SplashActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ActivitySplashBinding b = ActivitySplashBinding.inflate(getLayoutInflater());
        setContentView(b.getRoot());

        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            Prefs prefs = new Prefs(this);
            Intent next = prefs.onboardingDone()
                    ? new Intent(this, MainActivity.class)
                    : new Intent(this, OnboardingActivity.class);
            startActivity(next);
            finish();
        }, 1100);
    }
}
