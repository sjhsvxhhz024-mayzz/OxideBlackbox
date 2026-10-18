"""ProtoLife: digital organisms with spiking brains that learn by living.

No backprop, no datasets, no GPU. Each creature has:
  - a body with energy (a need) and metabolism that grows with brain size;
  - a brain of leaky integrate-and-fire neurons;
  - reward-modulated STDP: eligibility traces + "dopamine" = change in energy;
  - neurogenesis under stress and synaptic pruning;
  - a genome (learning rate, growth rate, threshold, initial wiring) that evolves.
The world regrows its own food, and food hotspots drift (seasons), so what
worked yesterday stops working - only adaptable creatures thrive.
"""
import argparse, json, time
import numpy as np

W_SIZE = 64
S, M = 7, 3            # sensors, motors (turn left, turn right, go)
NMAX = 32              # max neurons per brain
SUB = 4                # neural substeps per world tick
DIRS = np.array([(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)])


class World:
    def __init__(self, n=160, learning=True, seed=0):
        self.rng = np.random.default_rng(seed)
        self.learning = learning
        self.t = 0
        self.food = self.rng.random((W_SIZE, W_SIZE)) * 0.05
        self.next_id = 0
        self.P = 0
        self._alloc(n)
        for _ in range(n):
            self._spawn(None)

    # --- population storage (struct of arrays, batched brains) ---
    def _alloc(self, cap):
        self.cap = cap * 3
        c = self.cap
        self.alive = np.zeros(c, bool)
        self.pos = np.zeros((c, 2), int); self.head = np.zeros(c, int)
        self.energy = np.zeros(c); self.age = np.zeros(c, int)
        self.eaten = np.zeros(c); self.eaten_early = np.zeros(c)
        self.lineage = np.zeros(c, int); self.gen = np.zeros(c, int)
        self.W = np.zeros((c, NMAX, NMAX), np.float32); self.W0 = np.zeros((c, NMAX, NMAX), np.float32)
        self.E = np.zeros((c, NMAX, NMAX), np.float32)
        self.v = np.zeros((c, NMAX)); self.x = np.zeros((c, NMAX)); self.s = np.zeros((c, NMAX))
        self.active = np.zeros((c, NMAX), bool)
        self.g_lr = np.zeros(c); self.g_grow = np.zeros(c); self.g_th = np.zeros(c)
        self.g_hid0 = np.zeros(c, int)
        self.avg_r = np.zeros(c)

    def _spawn(self, parent):
        free = np.flatnonzero(~self.alive)
        if len(free) == 0:
            return
        i = free[0]; r = self.rng
        self.alive[i] = True; self.age[i] = 0; self.eaten[i] = 0; self.eaten_early[i] = 0
        self.v[i] = 0; self.x[i] = 0; self.s[i] = 0; self.E[i] = 0; self.avg_r[i] = 0
        if parent is None:
            self.pos[i] = r.integers(0, W_SIZE, 2); self.head[i] = r.integers(8)
            self.energy[i] = 1.0
            self.g_lr[i] = r.uniform(0.0, 0.05); self.g_grow[i] = r.uniform(0, 0.02)
            self.g_th[i] = r.uniform(0.6, 1.4); self.g_hid0[i] = r.integers(2, 8)
            self.W0[i] = r.normal(0, 0.5, (NMAX, NMAX))
            self.lineage[i] = self.next_id; self.gen[i] = 0
        else:
            p = parent
            self.pos[i] = self.pos[p]; self.head[i] = r.integers(8)
            self.energy[i] = self.energy[p] = self.energy[p] / 2
            mut = lambda x, s, lo, hi: float(np.clip(x + r.normal(0, s), lo, hi))
            self.g_lr[i] = mut(self.g_lr[p], 0.005, 0, 0.2)
            self.g_grow[i] = mut(self.g_grow[p], 0.002, 0, 0.1)
            self.g_th[i] = mut(self.g_th[p], 0.05, 0.3, 3)
            self.g_hid0[i] = int(np.clip(self.g_hid0[p] + r.integers(-1, 2), 0, NMAX - S - M))
            # genes carry the *innate* wiring; learned weights are not inherited
            self.W0[i] = self.W0[p] + r.normal(0, 0.08, (NMAX, NMAX))
            self.lineage[i] = self.lineage[p]; self.gen[i] = self.gen[p] + 1
        if not self.learning:
            self.g_lr[i] = 0.0
        self.active[i] = False
        self.active[i, :S + M + self.g_hid0[i]] = True
        self.W[i] = self.W0[i]
        self._mask(i)
        self.next_id += 1

    def _mask(self, i):
        a = self.active[i]
        self.W[i] *= np.outer(a, a)
        np.fill_diagonal(self.W[i], 0)
        self.W[i, :, :S] = 0        # nothing drives sensors except the world

    # --- senses ---
    def _sense(self, idx):
        p, h = self.pos[idx], self.head[idx]
        inp = np.zeros((len(idx), S))
        for k, dh in enumerate((-1, 0, 1)):
            d = DIRS[(h + dh) % 8]
            tot = 0
            for dist in (1, 2, 3):
                q = (p + d * dist) % W_SIZE
                tot = tot + self.food[q[:, 0], q[:, 1]] / dist
            inp[:, k] = tot * 2.0
        inp[:, 3] = self.food[p[:, 0], p[:, 1]] * 2
        inp[:, 4] = np.clip(1 - self.energy[idx], 0, 1) * 1.5   # hunger
        inp[:, 5] = self.rng.random(len(idx)) * 0.8               # spontaneous noise
        inp[:, 6] = 0.6                                           # tonic drive
        return inp

    def step(self):
        r = self.rng; self.t += 1
        # world: food regrows (logistic) and seeds neighbours; hotspots drift (seasons)
        ang = self.t / 1500.0
        cx = W_SIZE / 2 + 18 * np.cos(ang); cy = W_SIZE / 2 + 18 * np.sin(ang * 1.3)
        yy, xx = np.mgrid[0:W_SIZE, 0:W_SIZE]
        dx = np.minimum(abs(xx - cx), W_SIZE - abs(xx - cx)); dy = np.minimum(abs(yy - cy), W_SIZE - abs(yy - cy))
        fertile = 0.0003 + 0.012 * np.exp(-(dx ** 2 + dy ** 2) / 120)
        nb = (np.roll(self.food, 1, 0) + np.roll(self.food, -1, 0) + np.roll(self.food, 1, 1) + np.roll(self.food, -1, 1)) / 4
        self.food += fertile * (0.2 + nb) * (1 - self.food)
        np.clip(self.food, 0, 1, out=self.food)

        idx = np.flatnonzero(self.alive)
        if len(idx) == 0:
            return
        inp = self._sense(idx)
        W, v, x, s, E, act = self.W[idx], self.v[idx], self.x[idx], self.s[idx], self.E[idx], self.active[idx]
        th = self.g_th[idx][:, None]
        mot = np.zeros((len(idx), M))
        for _ in range(SUB):
            I = np.einsum('pi,pij->pj', s, W)
            I[:, :S] += inp
            v = v * 0.7 + I + r.normal(0, 0.05, v.shape)
            s = ((v > th) & act).astype(float)
            v[s > 0] = 0
            E *= 0.9
            E += x[:, :, None] * s[:, None, :] - 0.6 * s[:, :, None] * x[:, None, :]
            x = x * 0.7 + s
            mot += s[:, S:S + M]
        # act
        turn = (mot[:, 1] - mot[:, 0]).astype(int)
        self.head[idx] = (self.head[idx] + np.clip(turn, -1, 1)) % 8
        go = mot[:, 2] > 0
        self.pos[idx[go]] = (self.pos[idx[go]] + DIRS[self.head[idx[go]]]) % W_SIZE
        # eat
        p = self.pos[idx]
        bite = np.minimum(self.food[p[:, 0], p[:, 1]], 0.25)
        np.subtract.at(self.food, (p[:, 0], p[:, 1]), bite)
        np.clip(self.food, 0, 1, out=self.food)
        nh = act.sum(1) - S - M
        cost = 0.006 + 0.0003 * nh + 0.002 * go
        self.energy[idx] += bite - cost
        self.eaten[idx] += bite
        early = self.age[idx] < 150
        self.eaten_early[idx[early]] += bite[early]
        # dopamine = reward prediction error on energy change; pain when starving
        rwd = bite * 4 - 0.5 * (self.energy[idx] < 0.3)
        d = rwd - self.avg_r[idx]
        self.avg_r[idx] = 0.95 * self.avg_r[idx] + 0.05 * rwd
        W += self.g_lr[idx][:, None, None] * d[:, None, None] * E
        np.clip(W, -2, 2, out=W)
        W *= act[:, :, None] & act[:, None, :]
        W[:, :, :S] = 0
        self.W[idx], self.v[idx], self.x[idx], self.s[idx], self.E[idx] = W, v, x, s, E
        self.age[idx] += 1
        # neurogenesis under hunger, pruning of weak synapses
        stress = np.clip(1 - self.energy[idx], 0, 1)
        grow = r.random(len(idx)) < self.g_grow[idx] * stress
        for i in idx[grow]:
            off = np.flatnonzero(~self.active[i]);
            if len(off):
                self.active[i, off[0]] = True; self._mask(i)
        if self.t % 50 == 0:
            Wa = self.W[idx]; Wa[np.abs(Wa) < 0.02] = 0; self.W[idx] = Wa
        # death, birth
        dead = idx[(self.energy[idx] <= 0) | (self.age[idx] > 3000)]
        self.alive[dead] = False
        for i in idx[(self.energy[idx] > 2.0) & (self.age[idx] > 80)]:
            self._spawn(i)
        if self.alive.sum() < 40:            # immigrants keep the gene pool from collapsing
            for _ in range(5):
                self._spawn(None)
        self.last_dead = dead

    def stats(self):
        idx = np.flatnonzero(self.alive)
        nh = self.active[idx].sum(1) - S - M
        old = idx[self.age[idx] >= 300]
        rate_early = (self.eaten_early[old] / 150).mean() if len(old) else np.nan
        rate_late = ((self.eaten[old] - self.eaten_early[old]) / (self.age[old] - 150)).mean() if len(old) else np.nan
        return dict(t=self.t, pop=len(idx), energy=float(self.energy[idx].mean()),
                    neurons=float(nh.mean()), lr=float(self.g_lr[idx].mean()),
                    grow=float(self.g_grow[idx].mean()), gen=float(self.gen[idx].mean()),
                    maxgen=int(self.gen[idx].max()), lineages=int(len(np.unique(self.lineage[idx]))),
                    food=float(self.food.sum()), rate=float(self.eaten[idx].sum() / max(self.age[idx].sum(), 1)),
                    rate_early=float(rate_early), rate_late=float(rate_late))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ticks', type=int, default=20000)
    ap.add_argument('--no-learning', action='store_true')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--out', default='run.json')
    a = ap.parse_args()
    w = World(learning=not a.no_learning, seed=a.seed)
    log = []; t0 = time.time()
    for k in range(a.ticks):
        w.step()
        if w.t % 100 == 0:
            log.append(w.stats())
        if w.t % 2000 == 0:
            st = log[-1]
            print(f"t={w.t} pop={st['pop']} gen={st['gen']:.1f} neurons={st['neurons']:.1f} "
                  f"lr={st['lr']:.3f} rate={st['rate']:.4f} early={st['rate_early']:.4f} late={st['rate_late']:.4f} "
                  f"({w.t / (time.time() - t0):.0f} ticks/s)", flush=True)
    json.dump(log, open(a.out, 'w'))
    import pickle
    pickle.dump(w, open(a.out.replace('.json', '.pkl'), 'wb'))
