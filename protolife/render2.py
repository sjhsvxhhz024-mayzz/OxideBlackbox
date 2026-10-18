import json, pickle, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
import brain2 as B

plt.style.use('dark_background')
RUNS = [('v2_full', 'полный мозг', '#4fc3f7'), ('v2_plain', 'только дофамин', '#ffd54f'), ('v2_none', 'без обучения', '#ff8a65')]


def sm(y, k=10):
    y = np.array(y, float); y = np.where(np.isnan(y), np.nanmean(y), y)
    return np.convolve(y, np.ones(k) / k, 'valid')


def plots():
    data = {k: json.load(open(k + '.json')) for k, _, _ in RUNS}
    fig, ax = plt.subplots(2, 3, figsize=(16, 9))
    panels = [('rate', 'Питание (еда/тик) ↑'), ('pain', 'Доля тиков на яде ↓'), ('pop', 'Население'),
              ('gen', 'Поколение'), ('neurons', 'Нейронов коры'), ('lr', 'Ген скорости обучения')]
    for a, (k, name) in zip(ax.flat, panels):
        for key, lab, c in RUNS:
            d = data[key]; y = sm([x[k] for x in d]); a.plot([x['t'] for x in d][:len(y)], y, c=c, label=lab)
        a.set_title(name); a.grid(alpha=.2); a.set_xlabel('тик')
    ax[0, 0].legend(); fig.suptitle('ProtoLife v2: мозг из отделов с нейромедиаторами — сравнение', fontsize=15)
    fig.tight_layout(); fig.savefig('v2_compare.png', dpi=110)

    d = data['v2_full']; t = [x['t'] for x in d]
    fig, ax = plt.subplots(1, 2, figsize=(16, 5))
    cols = plt.cm.tab10(np.arange(7))
    for k, (m, ru) in enumerate(zip(B.MODS, B.MODS_RU)):
        y = sm([x[m] for x in d]); ax[0].plot(t[:len(y)], y, c=cols[k], label=ru)
    ax[0].set_title('Нейромедиаторы в популяции (среднее по особям)'); ax[0].legend(ncol=2, fontsize=8); ax[0].grid(alpha=.2)
    for m, ru, c in (('amy', 'ген скорости страха (миндалина)', '#ff5252'), ('sleep', 'ген склонности ко сну', '#b388ff')):
        y = sm([x[m] for x in d]); y = y / y[0]; ax[1].plot(t[:len(y)], y, c=c, label=ru)
    ax[1].set_title('Эволюция генов (относительно начала)'); ax[1].legend(); ax[1].grid(alpha=.2)
    fig.tight_layout(); fig.savefig('v2_modulators.png', dpi=110)


REG = [('таламус', range(0, 10), '#ffd54f'), ('гипоталамус', range(10, 12), '#ffab40'),
       ('миндалина', B.AMY, '#ff5252'), ('базальные ганглии', range(B.MOT, B.MOT + 3), '#ba68c8'),
       ('кора', range(B.CTX0, B.NMAX), '#90a4ae')]


def video(frames=450, every=3):
    w = pickle.load(open('v2_full.pkl', 'rb'))
    fig = plt.figure(figsize=(16, 8))
    aw = fig.add_axes([0.01, 0.05, 0.45, 0.88]); ab = fig.add_axes([0.48, 0.3, 0.3, 0.63])
    am = fig.add_axes([0.82, 0.3, 0.16, 0.6]); ak = fig.add_axes([0.5, 0.04, 0.46, 0.2])
    wr = FFMpegWriter(fps=30, bitrate=3500)
    with wr.saving(fig, 'v2_video.mp4', 100):
        for f in range(frames):
            for _ in range(every):
                w.step()
            idx = np.flatnonzero(w.alive); focus = idx[np.argmax(w.age[idx])]
            night = (w.t % B.DAY) > B.DAY * .7
            for a in (aw, ab, am, ak):
                a.clear()
            img = np.zeros((B.WS, B.WS, 3)); img[..., 1] = w.food; img[..., 0] = w.poison * .9
            aw.imshow(img * (.45 if night else 1), origin='lower')
            p = w.pos[idx]
            aw.scatter(p[:, 1], p[:, 0], c=np.where(w.asleep[idx], '#7e57c2', '#ffffff'), s=10 + 8 * np.clip(w.energy[idx], 0, 2))
            aw.scatter(*w.pos[focus][::-1], s=250, facecolors='none', edgecolors='#4fc3f7', lw=2)
            aw.set_title(f"{'НОЧЬ' if night else 'день'}  t={w.t}  население {len(idx)}  "
                         f"(зелёное=еда, красное=яд, фиолетовые=спят)", fontsize=10)
            aw.set_xticks([]); aw.set_yticks([])
            act = np.flatnonzero(w.active[focus]); xy = {}
            centers = [(-0.8, 0.6), (-0.8, -0.6), (0, -0.8), (0.85, 0), (0, 0.5)]
            for (name, rg, c), (cx, cy) in zip(REG, centers):
                ids = [i for i in rg if w.active[focus, i]]
                for k, i in enumerate(ids):
                    ang = 2 * np.pi * k / max(len(ids), 1)
                    rad = 0.12 + 0.025 * len(ids)
                    xy[i] = (cx + rad * np.cos(ang), cy + rad * np.sin(ang), c)
                ab.text(cx, cy + 0.2 + 0.025 * len(ids), name, ha='center', color=c, fontsize=8)
            Wf = w.W[focus]
            for i in act:
                for j in act:
                    if abs(Wf[i, j]) > .5:
                        ab.plot([xy[i][0], xy[j][0]], [xy[i][1], xy[j][1]], c='#4fc3f7' if Wf[i, j] > 0 else '#ff5252',
                                alpha=min(abs(Wf[i, j]) / 2.5, .5), lw=.7)
            sp = w.s[focus]
            ab.scatter([xy[i][0] for i in act], [xy[i][1] for i in act], c=[xy[i][2] for i in act],
                       s=[300 if sp[i] else 70 for i in act], edgecolors=['w' if sp[i] else 'none' for i in act], zorder=3)
            ab.set_xlim(-1.3, 1.3); ab.set_ylim(-1.3, 1.2); ab.axis('off')
            ab.set_title(f'Мозг старейшего существа: возраст {w.age[focus]}, поколение {w.gen[focus]}, энергия {w.energy[focus]:.2f}'
                         + (' — СПИТ' if w.asleep[focus] else ''), fontsize=10)
            vals = np.abs(w.mod[focus]); am.barh(B.MODS_RU[::-1], vals[::-1], color=plt.cm.tab10(np.arange(7))[::-1])
            am.set_xlim(0, 1); am.set_title('Нейромедиаторы', fontsize=10); am.tick_params(labelsize=8)
            ak.axis('off')
            ak.text(0, .5, 'Сенсоры → кора → моторы. Дофамин решает, какие связи усилить; норадреналин при сюрпризе ускоряет обучение;\n'
                    'ацетилхолин усиливает внимание; серотонин успокаивает; кортизол при стрессе растит новые нейроны;\n'
                    'окситоцин тянет к сородичам; мелатонин ночью усыпляет, и во сне связи коры ослабевают (гомеостаз).',
                    fontsize=8, va='center')
            wr.grab_frame()
            if f == frames // 2:
                fig.savefig('v2_frame.png', dpi=100)


if __name__ == '__main__':
    plots() if sys.argv[1] == 'plots' else video()
