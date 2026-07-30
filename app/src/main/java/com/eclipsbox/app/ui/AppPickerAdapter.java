package com.eclipsbox.app.ui;

import android.view.LayoutInflater;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.eclipsbox.app.databinding.ItemAppBinding;
import com.eclipsbox.app.model.AppEntry;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

public class AppPickerAdapter extends RecyclerView.Adapter<AppPickerAdapter.VH> {

    private final List<AppEntry> items = new ArrayList<>();
    private final Consumer<AppEntry> onPick;

    public AppPickerAdapter(Consumer<AppEntry> onPick) {
        this.onPick = onPick;
    }

    public void submit(List<AppEntry> newItems) {
        items.clear();
        items.addAll(newItems);
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        ItemAppBinding binding = ItemAppBinding.inflate(
                LayoutInflater.from(parent.getContext()), parent, false);
        return new VH(binding);
    }

    @Override
    public void onBindViewHolder(@NonNull VH holder, int position) {
        AppEntry e = items.get(position);
        holder.b.icon.setImageDrawable(e.icon);
        holder.b.label.setText(e.label);
        holder.b.pkg.setText(e.packageName);
        holder.b.getRoot().setOnClickListener(v -> onPick.accept(e));
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    static class VH extends RecyclerView.ViewHolder {
        final ItemAppBinding b;
        VH(ItemAppBinding b) {
            super(b.getRoot());
            this.b = b;
        }
    }
}
