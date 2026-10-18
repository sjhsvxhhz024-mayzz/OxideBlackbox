import json, pickle, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
import protolife as P

plt.style.use('dark_background')


def plots():
    L = json.load(open('learn.json')); C = json.load(open('ctrl.json'))
    t = lambda d: [x['t'] for x in d]
    sm = lambda y, k=10: np.convolve(np.nan_to_num(y, nan=np.nanmean(y)), np.ones(k) / k, 'valid')
    fig, ax = plt.subplots(2, 3, figsize=(16, 9))
    panels = [('pop', 'Население'), ('rate', 'Эффективность питания (еда/тик)'), ('neurons', 'Скрытых нейронов в мозге'),
              ('gen', 'Среднее поколение'), ('lr', 'Ген скорости обучения'), ('lineages', 'Число выживших родов')]
    for a, (k, name) in zip(ax.flat, panels):
        for d, lab, c in ((L, 'обучение при жизни', '#4fc3f7'), (C, 'контроль: только эволюция', '#ff8a65')):
            y = sm([x[k] for x in d]); a.plot(t(d)[:len(y)], y, c=c, label=lab)
        a.set_title(name); a.set_xlabel('тик'); a.grid(alpha=.2)
    ax[0, 0].legend()
    fig.suptitle('ProtoLife: цифровые организмы со спайковым мозгом', fontsize=16)
    fig.tight_layout(); fig.savefig('results.png', dpi=110)

    # lifetime learning: early-life vs later-life feeding rate of the same individuals
    fig, a = plt.subplots(figsize=(9, 5))
    for d, lab, c in ((L, 'обучение', '#4fc3f7'), (C, 'контроль', '#ff8a65')):
        e = sm([x['rate_early'] for x in d], 20); l = sm([x['rate_late'] for x in d], 20)
        a.plot(t(d)[:len(e)], l / e, c=c, label=lab)
    a.axhline(1, c='w', ls='--', alpha=.5)
    a.set_title('Учатся ли они при жизни?\n(питание во взрослом возрасте / в первые 150 тиков жизни; >1 = стали лучше)')
    a.set_xlabel('тик'); a.legend(); a.grid(alpha=.2)
    fig.tight_layout(); fig.savefig('lifetime_learning.png', dpi=110)


def video(pkl, out, frames=500, every=2):
    w = pickle.load(open(pkl, 'rb'))
    fig, (aw, ab) = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw=dict(width_ratios=[1, 1]))
    wr = FFMpegWriter(fps=30, bitrate=3000)
    ang = None
    with wr.saving(fig, out, 100):
        for f in range(frames):
            for _ in range(every):
                w.step()
            idx = np.flatnonzero(w.alive)
            focus = idx[np.argmax(w.age[idx])]
            aw.clear(); ab.clear()
            aw.imshow(w.food, cmap='Greens', vmin=0, vmax=1, origin='lower')
            p = w.pos[idx]
            aw.scatter(p[:, 1], p[:, 0], c=(w.lineage[idx] * 0.618) % 1, cmap='hsv', s=14 + 10 * np.clip(w.energy[idx], 0, 2))
            aw.scatter(*w.pos[focus][::-1], s=220, facecolors='none', edgecolors='w')
            aw.set_title(f'Мир  t={w.t}  население={len(idx)}  поколение до {w.gen[idx].max()}')
            aw.set_xticks([]); aw.set_yticks([])
            act = np.flatnonzero(w.active[focus]); n = len(act)
            th = np.linspace(0, 2 * np.pi, n, endpoint=False)
            xy = np.c_[np.cos(th), np.sin(th)]
            Wf = w.W[focus][np.ix_(act, act)]
            for i in range(n):
                for j in range(n):
                    if abs(Wf[i, j]) > 0.4:
                        ab.plot(*zip(xy[i], xy[j]), c='#4fc3f7' if Wf[i, j] > 0 else '#ff5252', alpha=min(abs(Wf[i, j]) / 2, .6), lw=.8)
            col = ['#ffd54f' if k < P.S else '#ba68c8' if k < P.S + P.M else '#90a4ae' for k in act]
            sp = w.s[focus][act] > 0
            ab.scatter(xy[:, 0], xy[:, 1], s=np.where(sp, 420, 120), c=col, edgecolors=np.where(sp, 'w', 'none'), zorder=3)
            ab.set_title(f'Мозг старейшего существа (обведено): возраст {w.age[focus]}, поколение {w.gen[focus]}\n'
                         f'{n - P.S - P.M} скрытых нейронов; жёлтые=сенсоры, фиолет.=моторы, вспышка=спайк;\n'
                         f'синие=возбуждающие, красные=тормозящие связи; энергия {w.energy[focus]:.2f}', fontsize=9)
            ab.set_xlim(-1.3, 1.3); ab.set_ylim(-1.3, 1.3); ab.axis('off')
            wr.grab_frame()
            if f == frames // 2:
                fig.savefig(out.replace('.mp4', '.png'), dpi=100)


if __name__ == '__main__':
    if sys.argv[1] == 'plots':
        plots()
    elif sys.argv[1] == 'newborn':
        w = P.World(seed=1); pickle.dump(w, open('newborn.pkl', 'wb'))
        video('newborn.pkl', 'video_start.mp4', frames=300)
    else:
        video('learn.pkl', 'video_evolved.mp4', frames=500)
