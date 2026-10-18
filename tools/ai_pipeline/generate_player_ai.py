import shutil
from gradio_client import Client, handle_file
def save(name, r):
    for it in (r if isinstance(r, (list, tuple)) else [r]):
        p = it.get("value", it.get("path")) if isinstance(it, dict) else it
        if isinstance(p, dict): p = p.get("path")
        if isinstance(p, str) and p.endswith((".glb", ".obj")):
            shutil.copy(p, f"tools/ai_pipeline/work/{name}_ai.glb"); print("SAVED", name, flush=True); return True
    print("NO_GLB", name, str(r)[:300], flush=True)
for name, img in (("rock", "tools/ai_pipeline/work/rock_in.png"), ("player", "tools/ai_pipeline/work/player_pre_v1.png")):
    for space, call in (("tencent/Hunyuan3D-2", lambda c, f: c.predict(None, f, None, None, None, None, 30, 5.0, api_name="/generation_all")),
                        ("tencent/Hunyuan3D-2", lambda c, f: c.predict(None, f, None, None, None, None, 30, 5.0, api_name="/shape_generation")),
                        ("stabilityai/stable-fast-3d", lambda c, f: c.predict(f, 0.85, "None", -1, 1024, api_name="/run_button"))):
        try:
            if save(name, call(Client(space, verbose=False), handle_file(img))): break
        except Exception as e:
            print("FAIL", name, space, repr(e)[:200], flush=True)
