"""Auto-rig the AI player with Make-It-Animatable (Hugging Face space) -> Mixamo-compatible skeleton."""
import shutil, sys, json
from gradio_client import Client, handle_file
src = sys.argv[1] if len(sys.argv) > 1 else "tools/ai_pipeline/work/player_hunyuan_raw.glb"
c = Client("jasongzy/Make-It-Animatable", verbose=False)
kw = dict(progress=handle_file(src), param_2=True, param_3="A-pose", param_4=[], param_5=False, param_6=0.01,
          param_7=False, param_8=True, param_9="LeftArm", param_10=True, param_12=True, param_13=True)
try:
    r = c.predict(**kw, param_11={"path": "/tmp/gradio/1e02c97f4fbed36b13d2dfe675c65e480f7411723e4d52a7bcfaa2caf5936ba7/Standard Run.fbx", "orig_name": "Standard Run.fbx", "meta": {"_type": "gradio.FileData"}}, api_name="/pipeline")
except Exception as e:
    print("default-anim call failed:", repr(e)[:300], flush=True)
    r = c.predict(**kw, param_11=None, api_name="/pipeline")
print(json.dumps(r, default=str)[:3000], flush=True)
for i, it in enumerate(r if isinstance(r, (list, tuple)) else [r]):
    p = it.get("value", it.get("path")) if isinstance(it, dict) else it
    if isinstance(p, dict): p = p.get("path")
    if isinstance(p, str) and p.split(".")[-1] in ("glb", "fbx", "obj", "npz", "ply"):
        dst = f"tools/ai_pipeline/work/mia_{i}.{p.split('.')[-1]}"
        shutil.copy(p, dst); print("SAVED", i, dst, flush=True)
