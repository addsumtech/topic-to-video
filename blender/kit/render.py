"""Engine set-up for a plate's two passes. Cycles renders on the GPU ONLY: on an Apple M4 with the CPU device also
enabled it took 67 s a frame at 128 spp, against 13-19 s at 64 spp on the GPU alone (measured 2026-11-04)."""
import bpy


def configure(sc, engine, mode, w, h, samples=64):
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = mode == "rgba"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    if engine == "cycles":
        sc.render.engine = "CYCLES"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = kind
            except TypeError:
                continue
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                break
        gpus = 0
        for d in prefs.devices:
            d.use = d.type != "CPU"
            gpus += d.use
        if not gpus:
            raise RuntimeError("Cycles needs a GPU device here (CPU rendering measured ~4x slower and is refused)")
        sc.cycles.device = "GPU"
        sc.cycles.samples = int(samples)
        sc.cycles.use_denoising = True
    else:
        sc.render.engine = "BLENDER_EEVEE"
        if hasattr(sc.eevee, "taa_render_samples"):
            sc.eevee.taa_render_samples = int(samples)
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass


def snapshot(sc):
    """What the ID pass changes, so it can be put back exactly."""
    return {"engine": sc.render.engine, "pct": sc.render.resolution_percentage,
            "vt": sc.view_settings.view_transform, "look": sc.view_settings.look,
            "transparent": sc.render.film_transparent}


def restore(sc, s):
    sc.render.engine = s["engine"]
    sc.render.resolution_percentage = s["pct"]
    sc.view_settings.view_transform = s["vt"]
    try:
        sc.view_settings.look = s["look"]
    except TypeError:
        pass
    sc.render.film_transparent = s["transparent"]
