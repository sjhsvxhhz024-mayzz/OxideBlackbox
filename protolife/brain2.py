"""ProtoLife v2: a spiking brain split into regions, with neuromodulators.

Regions (index ranges in each creature's neuron array):
  thalamus/senses  food L/C/R/here, poison L/C/R, others ahead, memory L/R
  hypothalamus     hunger, satiety (driven by the body)
  amygdala         fast-learning fear neurons, receive pain directly
  basal ganglia    motor output (left, right, go) with dopamine-gated action selection
  cortex           association neurons, grown by neurogenesis, pruned when weak
  hippocampus      remembers where food was found -> memory bearing signal
  cerebellum       learns to predict the next sensation; its error = surprise
Neuromodulators (one scalar each per creature):
  dopamine   reward prediction error -> sign and size of synaptic change
  serotonin  slow mood (average reward) -> patience, less random behaviour
  noradrenaline  sudden surprise -> arousal: more noise and faster learning
  acetylcholine  expected uncertainty -> attention: amplifies senses
  cortisol   chronic stress (hunger, pain) -> neurogenesis, metabolic cost
  oxytocin   company of others -> amplifies the social sense
  melatonin  night -> sleep: no movement, low metabolism, synaptic downscaling
All of it is a deliberately simplified model of these mechanisms, not biology.
"""
import argparse, json, pickle, time
import numpy as np

WS = 64
SENS = ['еда←', 'еда↑', 'еда→', 'еда здесь', 'яд←', 'яд↑', 'яд→', 'другие↑', 'память←', 'память→']
HYPO = ['голод', 'сытость']
S = len(SENS) + len(HYPO)          # 12 input neurons
AMY = range(S, S + 4)              # amygdala
MOT = S + 4                        # motors: MOT (left), MOT+1 (right), MOT+2 (go)
CTX0 = MOT + 3                     # first cortex neuron
NMAX = 44
SUB = 4
DAY = 1200
DIRS = np.array([(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)])
MODS = ['DA', '5HT', 'NE', 'ACh', 'cort', 'oxy', 'mel']
MODS_RU = ['дофамин', 'серотонин', 'норадреналин', 'ацетилхолин', 'кортизол', 'окситоцин', 'мелатонин']
NPRED = 4                          # cerebellum predicts the 4 food senses


def torus_d(a, b):
    d = (b - a) % WS
    return np.where(d > WS / 2, d - WS, d)


class World:
    def __init__(self, n=150, mode='full', seed=0):
        """mode: full | plain (dopamine-STDP only, no other modulators/regions) | none (no learning)"""
        self.rng = np.random.default_rng(seed)
        self.mode = mode
        self.t = 0
        self.food = self.rng.random((WS, WS)) * 0.05
        self.poison = np.zeros((WS, WS))
        self.next_id = 0
        c = self.cap = 450
        z = lambda *s, d=float: np.zeros((c,) + s, d)
        self.alive = z(d=bool); self.pos = z(2, d=int); self.head = z(d=int)
        self.energy = z(); self.age = z(d=int); self.eaten = z(); self.eaten_early = z()
        self.hurt = z(); self.lineage = z(d=int); self.gen = z(d=int)
        self.W = z(NMAX, NMAX, d=np.float32); self.W0 = z(NMAX, NMAX, d=np.float32)
        self.E = z(NMAX, NMAX, d=np.float32)
        self.v = z(NMAX); self.x = z(NMAX); self.s = z(NMAX); self.active = z(NMAX, d=bool)
        self.g = z(6)        # genes: lr, grow, threshold, n_cortex0, amygdala lr boost, sleep drive
        self.mod = z(len(MODS)); self.avg_r = z(); self.slow_err = z(); self.stress = z()
        self.Cb = z(NPRED, S + 3)         # cerebellum weights
        self.prev_in = z(S + 3)
        self.mem = z(2, d=int); self.mem_t = z(d=int) - 10 ** 6
        self.asleep = z(d=bool)
        for _ in range(n):
            self._spawn(None)

    def _spawn(self, p):
        free = np.flatnonzero(~self.alive)
        if not len(free):
            return
        i, r = free[0], self.rng
        for a in (self.v, self.x, self.s, self.E, self.mod, self.Cb, self.prev_in):
            a[i] = 0
        self.alive[i] = True; self.age[i] = 0; self.eaten[i] = self.eaten_early[i] = self.hurt[i] = 0
        self.avg_r[i] = self.slow_err[i] = self.stress[i] = 0; self.mem_t[i] = -10 ** 6; self.asleep[i] = False
        if p is None:
            self.pos[i] = r.integers(0, WS, 2); self.energy[i] = 1.0
            self.g[i] = [r.uniform(0, .05), r.uniform(0, .02), r.uniform(.6, 1.4), r.integers(2, 8), r.uniform(1, 5), r.uniform(0, 1)]
            self.W0[i] = r.normal(0, .5, (NMAX, NMAX))
            self.lineage[i] = self.next_id; self.gen[i] = 0
        else:
            self.pos[i] = self.pos[p]; self.energy[i] = self.energy[p] = self.energy[p] / 2
            lo = np.array([0, 0, .3, 0, 1, 0]); hi = np.array([.2, .1, 3, NMAX - CTX0, 10, 1])
            sd = np.array([.005, .002, .05, 1, .3, .05])
            self.g[i] = np.clip(self.g[p] + r.normal(0, 1, 6) * sd, lo, hi)
            self.g[i, 3] = round(self.g[i, 3])
            self.W0[i] = self.W0[p] + r.normal(0, .08, (NMAX, NMAX))   # innate wiring is inherited, learning is not
            self.lineage[i] = self.lineage[p]; self.gen[i] = self.gen[p] + 1
        self.head[i] = r.integers(8)
        if self.mode == 'none':
            self.g[i, 0] = 0
        self.active[i] = False; self.active[i, :CTX0 + int(self.g[i, 3])] = True
        self.W[i] = self.W0[i]; self._mask(i)
        self.next_id += 1

    def _mask(self, i):
        a = self.active[i]
        self.W[i] *= np.outer(a, a); np.fill_diagonal(self.W[i], 0)
        self.W[i, :, :S] = 0

    def _cones(self, field, p, h, rng):
        out = np.zeros((len(p), 3))
        for k, dh in enumerate((-1, 0, 1)):
            d = DIRS[(h + dh) % 8]
            for dist in range(1, rng + 1):
                q = (p + d * dist) % WS
                out[:, k] += field[q[:, 0], q[:, 1]] / dist
        return out

    def step(self):
        r = self.rng; self.t += 1; full = self.mode == 'full'
        night = (self.t % DAY) > DAY * 0.7
        # --- world: self-renewing food, drifting fertile zone and poison patches ---
        a = self.t / 1500.0
        yy, xx = np.mgrid[0:WS, 0:WS]
        def blob(cx, cy, s):
            dx = np.minimum(abs(xx - cx), WS - abs(xx - cx)); dy = np.minimum(abs(yy - cy), WS - abs(yy - cy))
            return np.exp(-(dx ** 2 + dy ** 2) / s)
        fertile = 0.0003 + 0.012 * blob(WS / 2 + 18 * np.cos(a), WS / 2 + 18 * np.sin(1.3 * a), 120)
        nb = sum(np.roll(self.food, k, ax) for k in (1, -1) for ax in (0, 1)) / 4
        self.food = np.clip(self.food + fertile * (.2 + nb) * (1 - self.food), 0, 1)
        self.poison = np.clip(blob(WS / 2 + 18 * np.cos(a + 2), WS / 2 + 18 * np.sin(1.3 * a + 2.5), 40)
                              + blob(WS / 2 + 20 * np.cos(-a + 4), WS / 2 + 14 * np.sin(a + 1), 30) - 0.25, 0, 1)

        idx = np.flatnonzero(self.alive)
        if not len(idx):
            return
        n = len(idx); p, h = self.pos[idx], self.head[idx]
        mod = self.mod[idx]
        vis = 3 if not night else 1
        # --- senses (thalamus) + hypothalamus ---
        inp = np.zeros((n, S))
        inp[:, 0:3] = self._cones(self.food, p, h, vis) * 2
        inp[:, 3] = self.food[p[:, 0], p[:, 1]] * 2
        inp[:, 4:7] = self._cones(self.poison, p, h, vis) * 2
        occ = np.zeros((WS, WS)); np.add.at(occ, (p[:, 0], p[:, 1]), 1)
        inp[:, 7] = self._cones(occ, p, h, 2)[:, 1] * .5
        if full:   # hippocampus: bearing to remembered food spot, fading with time
            dv = torus_d(p, self.mem[idx]); hd = DIRS[h]
            cross = hd[:, 0] * dv[:, 1] - hd[:, 1] * dv[:, 0]
            strength = np.exp(-(self.t - self.mem_t[idx]) / 400) * (np.abs(dv).sum(1) > 1)
            inp[:, 8] = (cross > 0) * strength * 1.5; inp[:, 9] = (cross < 0) * strength * 1.5
        inp[:, 10] = np.clip(1 - self.energy[idx], 0, 1) * 1.5
        inp[:, 11] = np.clip(self.energy[idx] - 1, 0, 1)
        if full:   # acetylcholine -> attention, oxytocin -> social sense
            inp[:, :7] *= (1 + mod[:, 3:4])
            inp[:, 7] *= (1 + 2 * mod[:, 5])
        on_poison = self.poison[p[:, 0], p[:, 1]]

        # --- spiking dynamics ---
        W, v, x, s, E, act = (self.W[idx], self.v[idx], self.x[idx], self.s[idx], self.E[idx], self.active[idx])
        th = self.g[idx, 2][:, None]
        noise = 0.05 * np.ones((n, 1))
        if full:   # noradrenaline raises noise (exploration), serotonin calms it
            noise = (0.05 + 0.25 * mod[:, 2:3]) * (1 - 0.5 * mod[:, 1:2])
        mot = np.zeros((n, 3))
        for _ in range(SUB):
            I = np.einsum('pi,pij->pj', s, W)
            I[:, :S] += inp
            if full:
                I[:, S:S + 4] += 2 * on_poison[:, None]          # pain goes straight to amygdala
            v = v * .7 + I + r.normal(0, 1, v.shape) * noise
            s = ((v > th) & act).astype(float); v[s > 0] = 0
            E *= .9
            E += x[:, :, None] * s[:, None, :] - .6 * s[:, :, None] * x[:, None, :]
            x = x * .7 + s
            mot += s[:, MOT:MOT + 3]

        # --- basal ganglia: action selection gated by tonic dopamine; sleep ---
        sleep = np.zeros(n, bool)
        if full:
            sleep = night & (self.energy[idx] > 0.6) & (r.random(n) < self.g[idx, 5])
        turn = np.sign(mot[:, 1] - mot[:, 0]).astype(int)
        go_th = 0 if not full else np.clip(0.5 - mod[:, 0], 0, 1)
        go = (mot[:, 2] > go_th) & ~sleep
        turn[sleep] = 0
        self.head[idx] = (h + turn) % 8
        self.pos[idx[go]] = (p[go] + DIRS[self.head[idx[go]]]) % WS
        p = self.pos[idx]

        # --- body ---
        bite = np.minimum(self.food[p[:, 0], p[:, 1]], .25) * ~sleep
        np.subtract.at(self.food, (p[:, 0], p[:, 1]), bite); np.clip(self.food, 0, 1, out=self.food)
        pain = self.poison[p[:, 0], p[:, 1]]
        nh = act.sum(1) - CTX0
        cost = (.006 + .0003 * nh + .002 * go) * np.where(sleep, .4, 1) + .03 * pain
        if full:
            cost += .002 * mod[:, 4]
        self.energy[idx] += bite - cost
        self.eaten[idx] += bite; self.hurt[idx] += pain > 0
        early = self.age[idx] < 150; self.eaten_early[idx[early]] += bite[early]
        if full:
            found = bite > .1
            self.mem[idx[found]] = p[found]; self.mem_t[idx[found]] = self.t

        # --- neuromodulators ---
        rwd = bite * 4 - .5 * (self.energy[idx] < .3) - 2 * pain
        da = rwd - self.avg_r[idx]
        self.avg_r[idx] = .95 * self.avg_r[idx] + .05 * rwd
        lr = self.g[idx, 0].copy()
        if full:
            cur = np.c_[inp, mot / SUB]
            pred = np.einsum('pk,pjk->pj', self.prev_in[idx], self.Cb[idx])
            err = inp[:, :NPRED] - pred
            self.Cb[idx] += .05 * err[:, :, None] * self.prev_in[idx][:, None, :]   # cerebellum delta rule
            self.prev_in[idx] = cur
            e = np.abs(err).mean(1)
            self.slow_err[idx] = .99 * self.slow_err[idx] + .01 * e
            self.stress[idx] = .995 * self.stress[idx] + .005 * (np.clip(1 - self.energy[idx], 0, 1) + pain)
            near = occ[p[:, 0], p[:, 1]] > 1
            m = mod
            m[:, 0] = np.tanh(da)
            m[:, 1] = .99 * m[:, 1] + .01 * np.clip(self.avg_r[idx] + .5, 0, 1)
            m[:, 2] = np.clip(.8 * m[:, 2] + .2 * np.clip((e - self.slow_err[idx]) * 5, 0, 1), 0, 1)
            m[:, 3] = np.clip(self.slow_err[idx] * 3, 0, 1)
            m[:, 4] = np.clip(self.stress[idx] * 2, 0, 1)
            m[:, 5] = .97 * m[:, 5] + .03 * near
            m[:, 6] = sleep.astype(float)
            self.mod[idx] = m
            lr = lr * (1 + 2 * m[:, 2]) * (1 + m[:, 3])
            neg = da < 0
            da = np.where(neg, da * (1 - .5 * m[:, 1]), da)     # serotonin softens disappointment
        else:
            self.mod[idx, 0] = np.tanh(da)
        dW = lr[:, None, None] * da[:, None, None] * E
        if full:   # amygdala synapses learn several times faster
            dW[:, :, S:S + 4] *= self.g[idx, 4][:, None, None]
        W += dW
        if full and sleep.any():    # sleep: synaptic homeostasis (down-scaling of cortex)
            W[sleep, CTX0:, :] *= .995; W[sleep, :, CTX0:] *= .995
        np.clip(W, -2, 2, out=W)
        W *= act[:, :, None] & act[:, None, :]; W[:, :, :S] = 0
        self.W[idx], self.v[idx], self.x[idx], self.s[idx], self.E[idx] = W, v, x, s, E
        self.age[idx] += 1
        self.asleep[idx] = sleep

        # --- neurogenesis (cortisol / hunger), pruning, death, birth ---
        drive = self.mod[idx, 4] if full else np.clip(1 - self.energy[idx], 0, 1)
        for i in idx[r.random(n) < self.g[idx, 1] * drive]:
            off = np.flatnonzero(~self.active[i])
            if len(off):
                self.active[i, off[0]] = True; self._mask(i)
        if self.t % 50 == 0:
            Wa = self.W[idx]; Wa[np.abs(Wa) < .02] = 0; self.W[idx] = Wa
        dead = idx[(self.energy[idx] <= 0) | (self.age[idx] > 3000)]
        self.alive[dead] = False
        for i in idx[(self.energy[idx] > 2) & (self.age[idx] > 80)]:
            self._spawn(i)
        if self.alive.sum() < 40:
            for _ in range(5):
                self._spawn(None)

    def stats(self):
        idx = np.flatnonzero(self.alive)
        old = idx[self.age[idx] >= 300]
        d = dict(t=self.t, pop=len(idx), energy=float(self.energy[idx].mean()),
                 neurons=float((self.active[idx].sum(1) - CTX0).mean()), lr=float(self.g[idx, 0].mean()),
                 gen=float(self.gen[idx].mean()), lineages=int(len(np.unique(self.lineage[idx]))),
                 rate=float(self.eaten[idx].sum() / max(self.age[idx].sum(), 1)),
                 pain=float(self.hurt[idx].sum() / max(self.age[idx].sum(), 1)),
                 sleep=float(self.g[idx, 5].mean()), amy=float(self.g[idx, 4].mean()),
                 rate_early=float((self.eaten_early[old] / 150).mean()) if len(old) else float('nan'),
                 rate_late=float(((self.eaten[old] - self.eaten_early[old]) / (self.age[old] - 150)).mean()) if len(old) else float('nan'))
        for k, name in enumerate(MODS):
            d[name] = float(np.abs(self.mod[idx, k]).mean())
        return d


def run(mode, ticks, seed, out):
    w = World(mode=mode, seed=seed); log = []; t0 = time.time()
    for _ in range(ticks):
        w.step()
        if w.t % 100 == 0:
            log.append(w.stats())
        if w.t % 2000 == 0:
            st = log[-1]
            print(f"{mode} t={w.t} pop={st['pop']} gen={st['gen']:.1f} rate={st['rate']:.4f} pain={st['pain']:.4f} "
                  f"ctx={st['neurons']:.1f} ({w.t / (time.time() - t0):.0f} t/s)", flush=True)
    json.dump(log, open(out + '.json', 'w')); pickle.dump(w, open(out + '.pkl', 'wb'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='full'); ap.add_argument('--ticks', type=int, default=20000)
    ap.add_argument('--seed', type=int, default=0); ap.add_argument('--out', default='v2_full')
    a = ap.parse_args()
    import brain2   # pickle the class under its module name so render scripts can load it
    brain2.run(a.mode, a.ticks, a.seed, a.out)
