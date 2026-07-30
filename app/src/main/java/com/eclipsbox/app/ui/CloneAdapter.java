package com.eclipsbox.app.ui;

import android.view.LayoutInflater;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.eclipsbox.app.databinding.ItemCloneBinding;
import com.eclipsbox.app.model.AppEntry;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

public class CloneAdapter extends RecyclerView.Adapter<CloneAdapter.VH> {

    private final List<AppEntry> items = new ArrayList<>();
    private final Consumer<AppEntry> onOpen;
    private final Consumer<AppEntry> onLongPress;

    public CloneAdapter(Consumer<AppEntry> onOpen, Consumer<AppEntry> onLongPress) {
        this.onOpen = onOpen;
        this.onLongPress = onLongPress;
    }

    public void submit(List<AppEntry> newItems) {
        items.clear();
        items.addAll(newItems);
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        ItemCloneBinding binding = ItemCloneBinding.inflate(
                LayoutInflater.from(parent.getContext()), parent, false);
        return new VH(binding);
    }

    @Override
    public void onBindViewHolder(@NonNull VH holder, int position) {
        AppEntry e = items.get(position);
        holder.b.icon.setImageDrawable(e.icon);
        holder.b.label.setText(e.label);
        holder.b.getRoot().setOnClickListener(v -> onOpen.accept(e));
        holder.b.getRoot().setOnLongClickListener(v -> {
            onLongPress.accept(e);
            return true;
        });
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    static class VH extends RecyclerView.ViewHolder {
        final ItemCloneBinding b;
        VH(ItemCloneBinding b) {
            super(b.getRoot());
            this.b = b;
        }
    }
}
