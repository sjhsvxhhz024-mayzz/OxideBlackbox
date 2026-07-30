package com.eclipsbox.app.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;

import androidx.appcompat.app.AppCompatActivity;

import com.eclipsbox.app.R;
import com.eclipsbox.app.databinding.ActivityOnboardingBinding;
import com.eclipsbox.app.util.Prefs;

/** Three-page intro. Lightweight manual pager (no extra deps). */
public class OnboardingActivity extends AppCompatActivity {

    private ActivityOnboardingBinding b;
    private int index = 0;

    private final int[] art = {
            R.drawable.onboard_1, R.drawable.onboard_2, R.drawable.onboard_3
    };
    private final int[] titles = {
            R.string.ob1_title, R.string.ob2_title, R.string.ob3_title
    };
    private final int[] bodies = {
            R.string.ob1_body, R.string.ob2_body, R.string.ob3_body
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        b = ActivityOnboardingBinding.inflate(getLayoutInflater());
        setContentView(b.getRoot());

        render();
        b.next.setOnClickListener(v -> {
            if (index < art.length - 1) {
                index++;
                render();
            } else {
                finishOnboarding();
            }
        });
        b.skip.setOnClickListener(v -> finishOnboarding());
    }

    private void render() {
        b.art.setImageResource(art[index]);
        b.title.setText(titles[index]);
        b.body.setText(bodies[index]);
        b.dot0.setSelected(index == 0);
        b.dot1.setSelected(index == 1);
        b.dot2.setSelected(index == 2);
        b.next.setText(index == art.length - 1 ? R.string.ob_start : R.string.ob_next);
        b.skip.setVisibility(index == art.length - 1 ? View.INVISIBLE : View.VISIBLE);
    }

    private void finishOnboarding() {
        new Prefs(this).setOnboardingDone(true);
        startActivity(new Intent(this, MainActivity.class));
        finish();
    }
}
